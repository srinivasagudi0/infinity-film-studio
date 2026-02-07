"""Entry point for Streamlit (cloud/local).

This delegates to `streamlit_app.py` so both files work:
- `streamlit run app.py` (Streamlit Cloud default)
- `streamlit run streamlit_app.py`
"""

from streamlit_app import main


if __name__ == "__main__":
    main()
