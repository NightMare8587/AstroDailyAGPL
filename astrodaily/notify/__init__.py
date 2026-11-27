"""Push notifications: a daily card message at the user's chosen local time.

Delivery is a separate run (``python -m astrodaily.tools.send_notifications``, started every few minutes by a
scheduler), not part of the web process, so a slow push service can never slow the API. Every send is
claimed in ``notification_log`` first, so overlapping or repeated runs never message anyone twice.
"""
