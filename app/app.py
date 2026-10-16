import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(project_root, ".env"))


def get_config_value(key, default=None):
    """Read Streamlit Cloud secrets, falling back to local environment variables."""
    try:
        return st.secrets.get(key, os.getenv(key, default))
    except FileNotFoundError:
        return os.getenv(key, default)


st.set_page_config(
    page_title="Movies Recommendation System",
    page_icon="🎬",
    layout="wide"
)

def get_db_connection():
    """Create a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=get_config_value("NEON_DB_NAME"),
            user=get_config_value("NEON_DB_USER"),
            password=get_config_value("NEON_DB_PASSWORD"),
            host=get_config_value("NEON_DB_HOST"),
            port=get_config_value("NEON_DB_PORT", "5432"),
            sslmode=get_config_value("NEON_DB_SSLMODE", "require")
        )
        return conn
    except Exception as e:
        st.error(f"Error connecting to the database: {e}")
        return None


@st.cache_data(ttl=600)
def fetch_filter_options():
    """Load filter values from the data already stored in PostgreSQL."""
    conn = get_db_connection()
    if conn is None:
        return {"genres": [], "languages": [], "release_years": []}

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT genre FROM public.movie_genres "
                "WHERE genre IS NOT NULL ORDER BY genre"
            )
            genres = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                "SELECT DISTINCT language FROM public.movie_info "
                "WHERE language IS NOT NULL ORDER BY language"
            )
            languages = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                "SELECT DISTINCT release_year FROM public.movie_info "
                "WHERE release_year IS NOT NULL ORDER BY release_year DESC"
            )
            release_years = [row[0] for row in cursor.fetchall()]

        return {
            "genres": genres,
            "languages": languages,
            "release_years": release_years,
        }
    except Exception as e:
        st.error(f"Error loading filter options: {e}")
        return {"genres": [], "languages": [], "release_years": []}
    finally:
        conn.close()


def fetch_movie_recommendation(genre=None, release_year=None,
                               language=None, score=None,
                               runtime_minutes=None):
    """Fetch data from the database using the provided SQL query."""
    conn = get_db_connection()
    if conn:
        try:
            base_query = """
                SELECT
                    mi.movie_id,
                    mi.name,
                    mi.release_year,
                    mi.language,
                    mi.score,
                    mi.runtime_minutes,
                    mi.status,
                    mi.budget,
                    mi.revenue,
                    mi.image,
                    mi.overview,
                    di.director_name,
                    mg.genre
                FROM public.movie_info mi
                JOIN public.movie_genres mg ON mi.movie_id = mg.movie_id
                JOIN public.director_info di ON mi.movie_id = di.movie_id
            """
            conditions = []
            if genre:
                conditions.append("mg.genre = %s")
            if release_year is not None:
                conditions.append("mi.release_year = %s")
            if language is not None:
                conditions.append("mi.language = %s")
            if score is not None and score > 0:
                conditions.append("mi.score >= %s")
            if runtime_minutes is not None and runtime_minutes > 0:
                conditions.append("mi.runtime_minutes <= %s")

            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
            base_query += " ORDER BY mi.release_year DESC"

            params = []
            if genre:
                params.append(genre)
            if release_year is not None:
                params.append(release_year)
            if language is not None:
                params.append(language)
            if score is not None and score > 0:
                params.append(score)
            if runtime_minutes is not None and runtime_minutes > 0:
                params.append(runtime_minutes)

            with conn.cursor() as cursor:
                cursor.execute(base_query, params)
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                df = pd.DataFrame(results, columns=columns)

                if not df.empty:
                    df['runtime_minutes'] = df['runtime_minutes'].apply(lambda x: round(x))
                    df['image'] = df['image'].apply(lambda x: x.replace("http://", "https://"))
                    df['release_year'] = pd.to_datetime(df['release_year'], format='%Y').dt.year
                    return df
                else:
                    # st.warning("Không có dữ liệu phù hợp với tiêu chí tìm kiếm.")
                    return pd.DataFrame(columns=columns)
        except Exception as e:
            st.error(f"Lỗi khi lấy dữ liệu: {e}")
        finally:
            conn.close()
    return pd.DataFrame()


def main():
    st.title("🎬 Movie Recommendation System")
    st.write("Find your next favorite movie!")
    st.sidebar.header("Filter Options")

    filter_options = fetch_filter_options()
    genre_options = ["Tất cả"] + filter_options["genres"]
    language_options = ["Tất cả"] + filter_options["languages"]
    year_options = ["Tất cả"] + filter_options["release_years"]

    selected_genre = st.sidebar.selectbox("Chọn Thể Loại Phim", genre_options)
    selected_year = st.sidebar.selectbox("Năm phát hành", year_options)
    selected_language = st.sidebar.selectbox("Chọn Ngôn Ngữ", language_options)
    score = st.sidebar.slider("Điểm Đánh Giá", 0, 100, 0)
    runtime_minutes = st.sidebar.number_input("Thời lượng (giờ)", min_value=0, step=1)

    # Fetch recommendations
    if st.sidebar.button("Get Recommendations"):
        with st.spinner("Đang tìm phim..."):
            recommendations = fetch_movie_recommendation(
                genre=None if selected_genre == "Tất cả" else selected_genre,
                release_year=None if selected_year == "Tất cả" else selected_year,
                language=None if selected_language == "Tất cả" else selected_language,
                score=score,
                runtime_minutes=runtime_minutes,
            )
            st.session_state["recommendations"] = recommendations
            st.session_state["selected_movie"] = None

    # Display recommendations or details
    if "selected_movie" in st.session_state and st.session_state["selected_movie"] is not None:
        idx = st.session_state["selected_movie"]
        movie = st.session_state["recommendations"].iloc[idx]
        st.subheader(f"📋 Chi tiết phim: {movie['name']}")
        st.image(movie['image'], width=200)
        st.write(f"**Thể loại**: {movie['genre']}")
        st.write(f"**Năm phát hành**: {movie['release_year']}")
        st.write(f"**Ngôn ngữ**: {movie['language']}")
        st.write(f"**Điểm đánh giá**: {movie['score']}/100")
        st.write(f"**Thời lượng**: {movie['runtime_minutes']} giờ")
        st.write(f"**Đạo diễn**: {movie['director_name']}")
        st.write(f"**Nội dung**: {movie['overview']}")
        if st.button("Quay về"):
            st.session_state["selected_movie"] = None
    elif "recommendations" in st.session_state and not st.session_state.get("selected_movie"):
        recommendations = st.session_state["recommendations"]

        if not recommendations.empty:
            st.write("### 🎥 Gợi ý phim cho bạn")
            cols = st.columns(5)

            for idx, row in recommendations.iterrows():
                with cols[idx % 5]:
                    st.image(row['image'], caption=row['name'], use_column_width=True)
                    if st.button("Xem chi tiết", key=f"details_btn_{idx}"):
                        st.session_state["selected_movie"] = idx
                        st.rerun()

        else:
            st.warning("Không tìm thấy phim phù hợp với tiêu chí. Vui lòng thay đổi tiêu chí lọc và thử lại.")

if __name__ == "__main__":
    main()