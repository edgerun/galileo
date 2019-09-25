cnt = 0


def next_request():
    global cnt
    cnt += 1
    return 'get', '/test', {'counter': cnt}
