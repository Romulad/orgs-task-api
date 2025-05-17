

def get_diff_objs(contain_diff:list, b:list):
    return [
        member for member in contain_diff if member not in b
    ]