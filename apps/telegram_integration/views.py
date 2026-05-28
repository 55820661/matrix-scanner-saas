import hmac
import json

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services import handle_update


def webhook_secret_valid(request, path_secret):
    configured = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    if not configured:
        return False
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    return hmac.compare_digest(path_secret, configured) or hmac.compare_digest(header_secret, configured)


@csrf_exempt
@require_POST
def telegram_webhook(request, secret):
    if not webhook_secret_valid(request, secret):
        return HttpResponseForbidden("Invalid Telegram webhook secret.")
    try:
        update = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)
    response_text = handle_update(update)
    return JsonResponse({"ok": True, "response": response_text})

