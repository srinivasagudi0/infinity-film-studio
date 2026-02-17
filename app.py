"""Streamlit launcher.

This keeps both entry commands working:
- `streamlit run app.py`
- `streamlit run streamlit_app.py`
"""

from streamlit_app import main


if __name__ == "__main__":
    main()
