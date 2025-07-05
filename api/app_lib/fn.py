

def get_diff_objs(contain_diff:list, b:list):
    """
    Returns a list of elements that are present in `contain_diff` but not in `b`.
    Args:
        contain_diff (list): The list of elements to compare.
        b (list): The list of elements to exclude from `contain_diff`.
    Returns:
        list: A list containing elements from `contain_diff` that are not in `b`.
    """
    
    return [
        member for member in contain_diff if member not in b
    ]