def clipboard_message(device_id, text):
    return {
        "type": "clipboard",
        "deviceId": device_id,
        "contentType": "text",
        "content": text
    }
