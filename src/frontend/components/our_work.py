from __future__ import annotations

from pathlib import Path

import streamlit as st


_THUMBNAIL = Path(__file__).resolve().parents[3] / "assets" / "driveway-landscaping.svg"


def render_our_work() -> None:
    """Render the featured driveway and landscaping project thumbnail."""
    st.markdown(
        """
        <section class="our-work" aria-labelledby="our-work-heading">
          <div class="panel-kicker">Project portfolio</div>
          <h2 id="our-work-heading">OUR WORK SPEAKS FOR ITSELF</h2>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.image(
        str(_THUMBNAIL),
        caption="Driveway & Landscaping — before and after",
        use_container_width=True,
    )
