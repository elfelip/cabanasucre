class SMBus:
    def __init__(self, bus=0):
        pass

    def write_byte(self, addr, cmd):
        pass

    def write_byte_data(self, addr, cmd, data):
        pass

    def write_block_data(self, addr, cmd, data):
        pass

    def read_byte(self, addr):
        return b'test'
    
    def read_byte_data(self, addr, cmd):
        return b'test'

    # read a block of data
    def read_block_data(self, addr, cmd):
        return b'test'