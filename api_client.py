


def get_key():
    with open("../conn.txt") as f:
        return f.readlines()[0]
    
