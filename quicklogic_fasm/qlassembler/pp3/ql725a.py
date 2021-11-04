#!/usr/bin/env python3
from quicklogic_fasm.qlassembler import QLAssembler as qlasm
from fasm import FasmLine
import os

class QL725AAssembler(qlasm.QLAssembler):

    bank_start_idx = [0, 664, 0, 664, 222, 443, 222, 443]

    def __init__(self, db, spi_master=True, osc_freq=False, ram_en=0, cfg_write_chcksum_post=True,
                cfg_read_chcksum_post=False, cfg_done_out_mask=False, add_header=True, add_checksum=True,
                verify_checksum=True):
        '''Class for generating bitstream for QuickLogic's QL725A FPGA.
        :param spi_master: True - assembler mode for SPI Master bitstream generation, False - SPI Slave
        :param osc_freq: internal oscillator frequency select True - high (20MHz), False - low (5MHz),
        :param ram_en: one-hot coded RAM access enable - when bit[i] is set to 1, it means ith RAM will be written,
        :param cfg_write_chcksum_post: UNUSED when spi_master==False
                True - Configuration Write Checksum Post: PolarProIII reads the data back and
                    performs the checksum after the data is written to Cfg Bit Cells and RAM.
                    This mode can verify not only the SPI bus integrity but also the data
                    integrity inside the Cfg Bit Cells and RAM. It will take a longer time
                    to configure the PolarProIII.
                False - Configuration Write Checksum Pre: PolarProIII performs the checksum before
                    the data is written to the Cfg Bit Cells and RAM. It can only verifies the
                    the integrity of SPI bus. It takes a shorter time to configure the PolarProIII.
,
        :param cfg_read_chcksum_post: Configuration Read Checksum Post - This command is for SPI Master
                                      to check the Status of PolarProIII. UNUSED when spi_master==True
        :param cfg_done_out_mask: cfg_done output mask, UNUSED when spi_master==True
                False - cfg_done output is masked, cfg_done is always 0
                True - cfg_done out is not masked, cfg_done reflects the status of PolarProIII
                PolarProIII defines 4 statuses:
                    IDLE: [2’b00, preamble[5:0]] - no command received after power up or SPI RESET.
                    BUSY: [2’b01, preamble[5:0]] - during the configuration write.
                    PASS: [2’b10, preamble[5:0]] - configuration completed, checksum is correct.
                    FAIL: [2’b11, preamble[5:0]] - configuration completed, checksum is incorrect.
        :param add_header: include PP3 specific header to the beginning of the final bitstream file
        :param add_checksum: include checksum for the configuration and RAM initialization payload
                             at the end of the final bitstream file

        Class inherits from QLAssembler class, and wraps it
        with ql725a specific parameters.
        :param MAXBL: the maximum value for bit line
        :param MAXWL: the maximum value for word line
        :param NUMOFBANKS: the number of config bit banks, source: QL3P1K.xml
        :param BANKSTARTBITIDX: contains the bit offset for a given bank, source: QL3P1K.xml
        '''
        self.spi_master = int(spi_master)
        self.osc_freq = int(osc_freq)
        self.ram_en = ram_en
        self.cfg_read_chcksum_post = int(cfg_read_chcksum_post)
        self.cfg_write_chcksum_post = int(cfg_write_chcksum_post)
        self.cfg_done_out_mask = int(cfg_done_out_mask)
        self.add_header = add_header
        self.add_checksum = add_checksum
        self.verify_checksum = bool(verify_checksum)

        self.BANKSTARTBITIDX = self.bank_start_idx
        self.MAXBL = 886
        self.MAXWL = 888
        self.NUMOFBANKS = 8
        super().__init__(db)

    def set_spi_master(self, spi_master=True):
        '''Changes the SPI mode of the bitstream writer.
        :param spi_master: True - assembler mode for SPI Master bitstream generation, False - SPI Slave
        '''
        self.spi_master = int(spi_master)


    def set_header(self, add_header=True):
        '''Changes the option whether to add or not a header to the bitstream file.
        :param add_header: include PP3 specific header to the beginning of the final bitstream file
        '''
        self.add_header = add_header


    def set_checksum(self, add_checksum=True):
        '''Changes the option whether to add or not a checksum to the bitstream file.
        :param add_checksum: include checksum for the configuration and RAM initialization payload
                             at the end of the final bitstream file
        '''
        self.add_checksum = add_checksum

    def calc_bitidx(self, banknum, bitnum):
        '''calculates the bit index (Y coordinate) and .

        Parameters
        ----------
        banknum: Bank number.
        bitnum: bit number in bank.
        '''
        if banknum in (4, 5, 6, 7):     # Banks with max bit line == 221
            if bitnum == 0:
                return -1
            else:
                return self.BANKSTARTBITIDX[banknum] + bitnum - 1
        else:
            return self.BANKSTARTBITIDX[banknum] + bitnum

    def produce_bitstream_header(self):
        header = []

        if (self.spi_master):
            command = ((self.cfg_write_chcksum_post << 1) | self.osc_freq) & 0b11
            command = ((~command << 2) | command) & 0b1111
            command = ((~command << 4) | command) & 0b11111111
        else:
            if (self.cfg_read_chcksum_post):
                command = (1 << 2) | (1 << 1) | self.osc_freq
            else:
                command = (self.cfg_write_chcksum_post << 1) | self.osc_freq
            command = (self.cfg_done_out_mask << 7) | command

        if (self.spi_master):
            header.append(0x59)         # fixed PP3-specific preamble
        header.append(command)          # internal oscillator frequency and checksum config
        header.append(self.ram_en)      # parameter 0 - one hot RAM enable config

        # parameters 1-3 - reserved
        for i in range(0, 3):
            header.append(0)

        return header;

    def checksum(self, data):
        crc_sum1 = 0
        crc_sum2 = 0

        words = [int.from_bytes(data[i:i+2], "little") \
                 for i in range(0, len(data), 2)]

        for word in words:
            crc_sum1 = (crc_sum1 + word)     & 0x0000FFFF
            crc_sum2 = (crc_sum2 + crc_sum1) & 0x0000FFFF

        c0 = (0x0000FFFF ^ ((crc_sum1 + crc_sum2) & 0x0000FFFF)) + 1
        c1 = (0x0000FFFF ^ ((crc_sum1 + c0)       & 0x0000FFFF)) + 1

        return (c1 << 16) | c0

    def produce_bitstream_checksum(self, bitstream):
        checksum = 0

        # FIXME: include RAM data in checksum calculation based on ram_en
        if (self.spi_master):
            checksum = self.checksum(bitstream[6:])
        else:
            checksum = self.checksum(bitstream[5:])

        checksum_bytes = checksum.to_bytes(4, "little")

        return checksum_bytes

    def format_outfile_name(self, outfilepath: str):
        if (not self.add_header and not self.add_checksum):
            if (outfilepath.endswith(".bit")):
                return outfilepath[:-4] + "_no_header_checksum.bit"
            else:
                return outfilepath + "_no_header_checksum"
        if (self.spi_master):
                return outfilepath
        else:
            if (outfilepath.endswith(".bit")):
                return outfilepath[:-4] + "_spi_slave.bit"
            else:
                return outfilepath + "_spi_slave"

    def produce_bitstream(self, outfilepath: str, verbose=False):
        def get_value_for_coord(wlidx, wlshift, bitidx):
            coord = (wlidx + wlshift, bitidx)
            if coord not in self.configbits:
                return -1
            else:
                return self.configbits[coord]

        bitstream = []

        if (self.add_header):
            bitstream = self.produce_bitstream_header()

        for wlidx in range(self.MAXWL // 2 - 1, -1, -1):
            for bitnum in range(0, self.BANKNUMBITS):
                currval = 0
                for banknum in range(self.NUMOFBANKS - 1, -1, -1):
                    val = 1
                    bitidx = self.calc_bitidx(banknum, bitnum)
                    if (bitidx == -1):
                        continue
                    if banknum in [2, 6, 7, 3]:
                        val = get_value_for_coord(wlidx, self.MAXWL // 2, bitidx)
                    else:
                        val = get_value_for_coord(wlidx, 0, bitidx)

                    if val == 1:
                        currval = currval | (1 << banknum)
                if verbose:
                    print('{}_{}:  {:02X}'.format(wlidx, bitnum, currval))
                bitstream.append(currval)

        if (self.add_checksum):
            bitstream += self.produce_bitstream_checksum(bitstream)

        if verbose:
            print('Size of bitstream:  {}B'.format(len(bitstream) * 4))

        bitfilepath = self.format_outfile_name(outfilepath)
        with open(bitfilepath, 'w+b') as output:
            for batch in bitstream:
                output.write(bytes([batch]))

        mem_file = os.path.join(os.path.dirname(outfilepath), "ram.mem")
        with open(mem_file, 'w') as output:
            for x,y in self.memdict.items():
                output.write("0x{:08x}:0x{:08x}\n".format(x,y))

    def populate_meminit(self, fasmline: FasmLine):
        raise NotImplementedError()

    def read_bitstream(self, bitfilepath):
        '''Reads bitstream from file.

        Parameters
        ----------
        bitfilepath: str
            A path to the binary file with bitstream
        '''

        # Load the bitstream
        with open(bitfilepath, "rb") as fp:
            bitstream = fp.read()

        # Handle header and CRC
        if self.add_header:
            if (bitstream[0] == 0x59):
                bitstream = bitstream[6:]
            else:
                bitstream = bitstream[5:]

        if self.add_checksum:
            crc_read = int.from_bytes(bitstream[-4:], "little")
            bitstream = bitstream[:-4]
        else:
            crc_read = None

        # Compute and check CRC
        if crc_read is not None:
            crc_calc = self.checksum(bitstream)

            if crc_calc != crc_read:
                msg = "CRC mismatch! (computed: {:08X}, read: {:08X})".format(
                    crc_calc, crc_read)

                if self.verify_checksum:
                    raise RuntimeError(msg)
                else:
                    print("WARNING: " + msg)

        # Check size, throw an error if too short
        # FIXME: Handle presence/absence of RAM init bits
        num_cfg_bits = self.MAXWL * self.MAXBL
        num_cfg_bytes = num_cfg_bits // 8
        if len(bitstream) < num_cfg_bytes:
            raise RuntimeError("Bitstream too short ({} vs {})".format(
                len(bitstream), num_cfg_bits // 8))

        # Trim if too long
        # FIXME: Handle presence/absence of RAM init bits
        if len(bitstream) > num_cfg_bits:
            print("WARNING: Bitstream too long ({} vs {}). Trimming...".format(
                len(bitstream), num_cfg_bits // 8))
            bitstream = bitstream[:(num_cfg_bits // 8)]

        # Decode config bits
        def set_bit(wlidx, wlshift, bitidx, value):
            coord = (wlidx + wlshift, bitidx)
            if value == 1:
                self.set_config_bit(coord, None)
            else:
                self.clear_config_bit(coord, None)

        val = iter(bitstream)
        for wlidx in reversed(range(self.MAXWL // 2)):
            for bitnum in range(self.BANKNUMBITS):
                currval = next(val)
                for banknum in reversed(range(self.NUMOFBANKS)):
                    bit = (currval >> banknum) & 1
                    bitidx = 0

                    bitidx = self.calc_bitidx(banknum, bitnum)
                    if (bitidx == -1):
                        continue

                    if banknum in [2, 6, 7, 3]:
                        set_bit(wlidx, self.MAXWL // 2, bitidx, bit)
                    else:
                        set_bit(wlidx, 0, bitidx, bit)
