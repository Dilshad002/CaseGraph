from backend.graph.connection import get_session

def test_connection():
    with get_session() as session:
        result = session.run("RETURN 'connection working' AS message")
        print(result.single()["message"])
        
if __name__ == "__main__":
    test_connection()