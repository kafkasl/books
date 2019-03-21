ps -elfa | grep books_server | awk '{print $4}' | xargs sudo kill -9
