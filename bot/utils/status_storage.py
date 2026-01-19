STATUS_CHANNEL_ID = None
STATUS_MESSAGE_ID = None

def set_status_message(channel_id: int, message_id: int):
    global STATUS_CHANNEL_ID, STATUS_MESSAGE_ID
    STATUS_CHANNEL_ID = channel_id
    STATUS_MESSAGE_ID = message_id

def get_status_message():
    return STATUS_CHANNEL_ID, STATUS_MESSAGE_ID
