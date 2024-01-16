import serial, struct

class SBBTarget(serial.Serial):

    sigvals_request = b'\x01'
    exectime_request = b'\x02'
    signames_request = b'\x03'
    split_char = b'\x00'

    def __init__(self):
        super().__init__()

    def get_signames(self):
        # Send request byte
        try:
            if self.write(self.signames_request) < 1:
                return []
        except serial.SerialException as e:
            return []

        # Read line
        line = self.readline()

        # Decode
        signames = line.decode("utf-8").split('\0')
        del signames[-1]  
        return signames

    def get_signals(self, num_sig: int):   
        # Send request byte
        try:
            if self.write(self.sigvals_request) < 1:
                return None, None
        except serial.SerialException as e:
            return None, None

        # Read data
        data_bytes = self.read(num_sig*4)
        if len(data_bytes) < (num_sig*4): # Not enough bytes read...
            return None, None
        
        # Convert data to floats and return
        return struct.unpack('f' * num_sig, data_bytes), data_bytes

    def get_exectime(self):
        # Send request byte
        try:
            if self.write(self.exectime_request) < 1:
                return None
        except serial.SerialException as e:
            return None

        # Read data
        exectime_bytes = self.read(4)
        if len(exectime_bytes) < 4:  # Not enough bytes read...
            return None

        return struct.unpack('f', exectime_bytes)[0]
            
