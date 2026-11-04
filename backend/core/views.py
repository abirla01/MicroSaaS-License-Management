import json

from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from licensing.services import validate_license


@csrf_exempt
@require_POST
def login_api(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return JsonResponse(
            {"error": "Username and password are required."},
            status=400,
        )

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if user is None:
        return JsonResponse(
            {"error": "Invalid username or password."},
            status=401,
        )

    if not user.is_active:
        return JsonResponse({"error": "Account is inactive."}, status=403)

    refresh = RefreshToken.for_user(user)

    role = (
        "owner"
        if user.role == User.Role.ADMIN
        else "customer"
    )

    return JsonResponse({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.pk,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": role,
        },
    })


@csrf_exempt
def validate_license_api(request):
    if request.method != "POST":
        return JsonResponse({"detail": "POST required"}, status=405)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"valid": False, "reason": "INVALID_JSON"},
            status=400,
        )

    result = validate_license(data.get("license_key", ""))

    return JsonResponse(
        result,
        status=200 if result.get("valid") else 403,
    )