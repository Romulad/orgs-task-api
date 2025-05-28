from app_lib.views import FullModelViewSet
from app_lib.queryset import queryset_helpers
from tasks.serializers import (
    TaskSerializer, 
    TaskDetailSerializer, 
    CreateTaskSerializer
)


class TaskViewSet(FullModelViewSet):
    serializer_class = TaskSerializer
    queryset = queryset_helpers.get_task_queryset()

    def get_serializer(self, *args, **kwargs):
        if self.action == 'create':
            kwargs['context'] = self.get_serializer_context()
            return CreateTaskSerializer(*args, **kwargs)
        elif self.action == 'retrieve':
            return TaskDetailSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)