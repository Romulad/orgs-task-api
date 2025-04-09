from django.utils.translation import gettext_lazy as _

def validate_password(password:str):
    "Return `True` if password is in a valid format or an error message"
    l = []

    for el in password:
        l.append(el)
        
    upper_letters = [u for u in l if str(u).isupper()]

    if len(password) < 8:
        return _('Your password must contain at least 8 characters')
    
    elif password.isdigit():
        return _('Your password should not contain only number')
    
    elif len(upper_letters) < 1 :
        return _('Your password must include an upper letter')
    
    elif ('1' not in l) and ('0' not in l) and ('2' not in l) and ('3' not in l) and ('4' not in l) and ('5' not in l) and ('6' not in l) and ('7' not in l) and ('8' not in l) and ('9' not in l):
        return _("Your password must include at least one digit")
    
    elif ('@' not in l) and ('.' not in l) and ('+' not in l) and ('-' not in l) and ('/' not in l) and ('_' not in l):
        return _('Your password must include at least one of these characters : @ . + - / _ ')
    
    else:
        return True
