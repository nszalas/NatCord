from django.shortcuts import redirect


def admin_required(view_func):

    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated or not (request.user.role == 'admin' or request.user.is_superuser):
            return redirect('/channels/')

        return view_func(request, *args, **kwargs)

    return wrapper


def moderator_required(view_func):

    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated or not (
            request.user.role in ['admin', 'moderator'] or request.user.is_superuser
        ):
            return redirect('/channels/')

        return view_func(request, *args, **kwargs)

    return wrapper
