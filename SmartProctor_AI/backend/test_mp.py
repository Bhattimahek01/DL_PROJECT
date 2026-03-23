try:
    from mediapipe.python.solutions import face_mesh as mp_face_mesh
    print(f"Face Mesh (via python.solutions): {mp_face_mesh}")
except Exception as e:
    print(f"Error (via python.solutions): {e}")

try:
    import mediapipe as mp
    print(f"Mediapipe version: {mp.__version__}")
    print(f"Mediapipe dir: {dir(mp)}")
except Exception as e:
    print(f"Error (direct): {e}")
