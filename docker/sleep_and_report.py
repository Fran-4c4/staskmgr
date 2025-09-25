import sys
import time
import json
import os

def main():
    try:
        sleep_time = int(sys.argv[1]) if len(sys.argv) > 1 else 5
        path_to_check = sys.argv[2] if len(sys.argv) > 2 else "/data"

        
        path_exists = os.path.exists(path_to_check)

        result = {
            "status": "completed",
            "slept_seconds": sleep_time,
            "path_checked": path_to_check,
            "path_exists": path_exists,
            "message": "Process finished successfully"
        }
        print(json.dumps(result))
        time.sleep(sleep_time)
        sys.exit(0)

    except Exception as e:
        error_result = {
            "status": "error",
            "message": str(e)
        }
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == "__main__":
    main()
