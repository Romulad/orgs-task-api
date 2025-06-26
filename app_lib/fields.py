from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from rest_framework.utils import html

class AllowBlankMixin:
    """A mixin to allow blank values in serializers.
    This mixin can be used with any serializer field to allow blank values
    while still performing validation. If `allow_blank` is set to True, the field
    will return None for blank values instead of raising a validation error.
    A Blank value is considered an empty string ('').
    """
    # for context: 
    # it was necessary to create this mixin because a serializer field like
    # DateTimeField does not have a `allow_blank` argument, so we cannot use
    # the `allow_blank` argument directly in the field definition.
    # This can be usefull in a update(PUT) operation where all fields should be 
    # included, but some of them can be blank.
    def __init__(self, allow_blank=False, **kwargs):
        self.allow_blank = allow_blank
        super().__init__(**kwargs)

    def to_internal_value(self, value):
        try:
            data = super().to_internal_value(value)
        except serializers.ValidationError:
            if self.allow_blank and value == '':
                return None
            raise
        except Exception:
            raise
        else:
            return data
        

class ManyPrimaryKeyRelatedField(serializers.RelatedField):
    """A field for handling many-to-many relationships using primary keys.
    This field can be used to serialize and deserialize lists of primary keys
    for related objects. It can also accept a serializer class `serializer_class` to provide more
    detailed serialization of the related objects.
    """

    default_error_messages = {
        'invalid': _('Invalid data'),
        'required': _('This field is required.'),
        'does_not_exist': _('Invalid value "{pk_value}" - object does not exist.'),
        'empty': _("This list may not be empty."),
    }

    def __init__(self, serializer_class=None, allow_empty=False, **kwargs):
        self.serializer_class = serializer_class
        self.allow_empty = allow_empty
        super().__init__(**kwargs)

    def to_representation(self, data):
        serializer_class = self.serializer_class
        if serializer_class is not None:
            return serializer_class(data, many=True).data
        data = data.all()
        return [value.pk for value in data]

    def to_internal_value(self, pk_values:list):
        if not isinstance(pk_values, list):
            self.fail('invalid')
        
        if not self.allow_empty and len(pk_values) == 0:
            self.fail("empty")
        
        if len(pk_values) == 0:
            return []
            
        data = list(self.get_queryset().filter(pk__in=pk_values))
        found_ids = [str(obj.pk) for obj in data]
        
        for pk_value in pk_values:
            if pk_value not in found_ids:
                self.fail('does_not_exist', pk_value=pk_value)
        
        return data

    def get_value(self, dictionary):
        # We override the default field access in order to support
        # lists in HTML forms.
        if html.is_html_input(dictionary):
            # Don't return [] if the update is partial
            if self.field_name not in dictionary:
                if getattr(self.root, 'partial', False):
                    return serializers.empty
            return dictionary.getlist(self.field_name)

        return dictionary.get(self.field_name, serializers.empty)



class DefaultDateTimeField(AllowBlankMixin, serializers.DateTimeField):
    pass