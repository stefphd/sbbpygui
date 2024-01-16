
def valid_baud(baudstr: str):
    try:
        baud = int(baudstr)
        if baud <= 0:
            return False
    except ValueError:
        return False
    return True

def valid_timeout(timeoutstr: str):
    try:
        timeout = int(timeoutstr)
        if timeout <= 0:
            return False
    except ValueError:
        return False
    return True