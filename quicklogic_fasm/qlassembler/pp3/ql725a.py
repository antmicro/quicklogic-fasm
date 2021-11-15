#!/usr/bin/env python3
from quicklogic_fasm.qlassembler import QLAssembler as qlasm
from fasm import FasmLine
import os

class QL725AAssembler(qlasm.QLAssembler):

    bank_start_idx = [0, 664, 0, 664, 222, 443, 222, 443]
    rambaseaddress = {'X1Y1' : '0x3000', 'X18Y1' : '0x2000', 'X1Y34' : '0x0000', 'X18Y34' : '0x1000'}
    # All RAMs disabled by default; ram_bank_block_en['X1Y34'][1] --> enable state of block 1 in RAM Bank2
    ram_bank_map = {'X1Y1' : 0, 'X18Y1' : 1, 'X1Y34' : 2, 'X18Y34' : 3}
    inv_ram_bank_map = {val: key for key, val in ram_bank_map.items()}
    ram_bank_block_en = {'X1Y1' : [0, 0], 'X18Y1' : [0, 0], 'X1Y34' : [0, 0], 'X18Y34' : [0, 0]}
    ram_init_config = {}

    INIT_BITS_PER_RAM_CELL = 18
    TOTAL_BITS_PER_RAM_CELL = 32
    CELLS_PER_RAM_BLOCK = 512
    RAM_PADDING = TOTAL_BITS_PER_RAM_CELL - INIT_BITS_PER_RAM_CELL
    BYTES_PER_RAM_BLOCK = CELLS_PER_RAM_BLOCK * TOTAL_BITS_PER_RAM_CELL // 8

    def __init__(self, db, spi_master=True, osc_freq=False, cfg_write_chcksum_post=True,
                cfg_read_chcksum_post=False, cfg_done_out_mask=False, add_header=True, add_checksum=True,
                verify_checksum=True):
        '''Class for generating bitstream for QuickLogic's QL725A FPGA.
        :param spi_master: True - assembler mode for SPI Master bitstream generation, False - SPI Slave
        :param osc_freq: internal oscillator frequency select True - high (20MHz), False - low (5MHz),
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
        self.ram_en = 0 # One-hot coded RAM access enable
        super().__init__(db)
        self.membaseaddress = self.rambaseaddress

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

        for bankname, blocks in self.ram_bank_block_en.items():
            block_no = 0
            for block_en in blocks:
                bit = (self.ram_bank_map[bankname] * 2) + block_no
                if (block_en):
                    self.ram_en |= (block_en << bit)
                else:
                    self.ram_en &= ~(1 << bit)
                block_no += 1

        header.append(self.ram_en)

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

    def prepare_ram_init_data(self):
        ram_init_data = []

        for bit_no in range(8):
            block_en = (self.ram_en >> bit_no) & 1
            if (block_en):
                block_no = bit_no % 2
                bank_no = bit_no // 2
                bank_name = self.inv_ram_bank_map[bank_no]
                bank_base_addr = int(self.rambaseaddress[bank_name], 16)
                block_base_addr = bank_base_addr + (self.BYTES_PER_RAM_BLOCK * block_no)
                for i in range(self.CELLS_PER_RAM_BLOCK):
                    bytes_per_cell = self.TOTAL_BITS_PER_RAM_CELL // 8
                    ram_addr = block_base_addr + (i * bytes_per_cell)
                    ram_data = self.memdict[ram_addr]
                    for byte_no in range(bytes_per_cell):
                        ram_byte = (ram_data >> (8 * byte_no)) & 0xFF
                        ram_init_data.append(ram_byte)
        return ram_init_data

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

        ram_data = self.prepare_ram_init_data()
        bitstream += ram_data

        if (self.add_checksum):
            bitstream += self.produce_bitstream_checksum(bitstream)

        if verbose:
            print('Size of bitstream:  {}B'.format(len(bitstream) * 4))

        bitfilepath = self.format_outfile_name(outfilepath)
        with open(bitfilepath, 'w+b') as output:
            for batch in bitstream:
                output.write(bytes([batch]))

    def populate_meminit(self, fasmline: FasmLine):
        featurevalue = fasmline.set_feature.value
        bankname = fasmline.set_feature.feature[:-13]
        baseaddress = int (self.membaseaddress[bankname], 16)
        bankconfigsize = ((fasmline.set_feature.end + 1) // self.INIT_BITS_PER_RAM_CELL) - (fasmline.set_feature.start // self.INIT_BITS_PER_RAM_CELL)

        assert bankconfigsize in {self.CELLS_PER_RAM_BLOCK, self.CELLS_PER_RAM_BLOCK * 2}, "Wrong RAM init bits amount: {} for bank: {}".format(bankconfigsize, bankname)

        # Fill ram_enable dataset
        if (bankconfigsize == self.CELLS_PER_RAM_BLOCK):
            if (fasmline.set_feature.start == 0):       # Enable Block0
                self.ram_bank_block_en[bankname][0] = 1
            elif (fasmline.set_feature.start == self.CELLS_PER_RAM_BLOCK * self.INIT_BITS_PER_RAM_CELL):  # Enable Block1
                self.ram_bank_block_en[bankname][1] = 1
            else:
                raise ValueError("Incorrect start bit value: {} for feature: {}".format(fasmline.set_feature.start, bankname))
        else:
            self.ram_bank_block_en[bankname][0] = 1     # Enable both RAM Blocks
            self.ram_bank_block_en[bankname][1] = 1

        # Save memory configuration
        for i in range(fasmline.set_feature.start // self.INIT_BITS_PER_RAM_CELL, (fasmline.set_feature.end + 1) // self.INIT_BITS_PER_RAM_CELL):
            value = featurevalue & 0x3FFFF
            featurevalue = featurevalue >> self.INIT_BITS_PER_RAM_CELL
            self.memdict[baseaddress+i*4] = value;

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
                ram_en = bitstream[2]
                bitstream = bitstream[6:]
            else:
                ram_en = bitstream[1]
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

        # Get size of RAM initialization bits
        ram_init_bytes = 0
        for bit_no in range(8):
            block_en = (ram_en >> bit_no) & 1
            if (block_en):
                ram_init_bytes += self.BYTES_PER_RAM_BLOCK

        # Get size of configuration bits
        num_cfg_bits = self.BANKNUMBITS * self.NUMOFBANKS * self.MAXWL // 2
        num_cfg_bytes = num_cfg_bits // 8

        # Check size, throw an error if too short
        exp_bitstream_size = num_cfg_bytes + ram_init_bytes
        if len(bitstream) < exp_bitstream_size:
            raise RuntimeError("Bitstream too short ({} vs {})".format(
                len(bitstream), exp_bitstream_size))

        # Trim if too long
        if len(bitstream) > exp_bitstream_size:
            print("WARNING: Bitstream too long ({} vs {}). Trimming...".format(
                len(bitstream), exp_bitstream_size))
            bitstream = bitstream[:exp_bitstream_size]

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

        # Read RAM init bits
        for ram_bank in range(4):
            bank = []
            for ram_block in range(2):
                block = []
                block_en = (ram_en >> ((ram_bank * 2) + ram_block)) & 1
                if (block_en):
                    for ram_byte in range(self.BYTES_PER_RAM_BLOCK):
                        currval = next(val)
                        block.append(currval)
                bank.append(block)
            self.ram_init_config[self.inv_ram_bank_map[ram_bank]] = bank

