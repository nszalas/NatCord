from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import admin_required, moderator_required
from .forms import RegisterForm, UserRoleForm, UserUpdateForm

User = get_user_model()


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            messages.success(request, "Account created. You can log in now.")
            return redirect("/login/")
    else:
        form = RegisterForm()

    return render(request, "auth/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid username or password.")
        elif user.is_blocked:
            messages.error(request, "This account has been blocked.")
        else:
            login(request, user)
            return redirect("/channels/")

    return render(request, "auth/login.html")


def logout_view(request):
    logout(request)
    return redirect("/login/")


@login_required
def profile_view(request):
    user_form = UserUpdateForm(instance=request.user)

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, "Profile saved.")
            return redirect("/profile/")

    return render(request, "auth/profile.html", {"user_form": user_form})


@login_required
@moderator_required
def user_admin_list(request):
    users = User.objects.order_by("username")
    return render(request, "auth/user_admin_list.html", {"users": users})


@login_required
@admin_required
def change_user_role(request, user_id):
    edited_user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        form = UserRoleForm(request.POST, instance=edited_user)
        if form.is_valid():
            form.save()
            messages.success(request, "User role has been updated.")
    return redirect("/users/")


@login_required
@moderator_required
def toggle_block_user(request, user_id):
    edited_user = get_object_or_404(User, id=user_id)
    if edited_user == request.user:
        messages.error(request, "You cannot block your own account.")
    elif edited_user.role == "admin" and request.user.role != "admin" and not request.user.is_superuser:
        messages.error(request, "A moderator cannot block an administrator.")
    else:
        edited_user.is_blocked = not edited_user.is_blocked
        edited_user.save(update_fields=["is_blocked"])
        messages.success(request, "Block status has been changed.")
    return redirect(request.META.get("HTTP_REFERER", "/users/"))


@login_required
@moderator_required
def delete_user(request, user_id):
    edited_user = get_object_or_404(User, id=user_id)
    if edited_user == request.user:
        messages.error(request, "You cannot delete your own account.")
    elif request.user.role == "moderator" and edited_user.role in ["admin", "moderator"]:
        messages.error(request, "A moderator can delete regular users only.")
    elif edited_user.is_superuser and not request.user.is_superuser:
        messages.error(request, "You cannot delete a superuser.")
    else:
        username = edited_user.username
        edited_user.delete()
        messages.success(request, f"User {username} has been deleted.")
    return redirect("/users/")
