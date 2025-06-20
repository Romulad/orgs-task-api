from app_lib.filter import BaseNameDescriptionDateDataFilter as BaseFilter


class TagDataFilter(BaseFilter):
    
    class Meta(BaseFilter.Meta):
        fields = [
            *BaseFilter.Meta.fields,
            'org'
        ]