from django import template
from ..models import ChatNotification, ChatRequest

register = template.Library()

@register.simple_tag
def unread_chat_count(user):
    """Get unread chat notifications count"""
    return ChatNotification.objects.filter(user=user, is_read=False).count()

@register.simple_tag
def get_pending_requests_count(user):
    """Get pending chat requests count (for Admin/CEO)"""
    if hasattr(user, 'role') and user.role.role in ['admin', 'ceo']:
        return ChatRequest.objects.filter(status='pending').count()
    return 0