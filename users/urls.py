from django.urls import path
from .views import (
    change_user_role,
    delete_user,
    login_view,
    logout_view,
    profile_view,
    register_view,
    toggle_block_user,
    user_admin_list,
)

urlpatterns = [
    path('register/', register_view),
    path('login/', login_view),
    path('logout/', logout_view),
    path('profile/', profile_view, name='profile'),
    path('users/', user_admin_list, name='user_admin_list'),
    path('users/<int:user_id>/role/', change_user_role, name='change_user_role'),
    path('users/<int:user_id>/block/', toggle_block_user, name='toggle_block_user'),
    path('users/<int:user_id>/delete/', delete_user, name='delete_user'),
]
