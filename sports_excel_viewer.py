import streamlit as st
import pandas as pd
from io import BytesIO
import polars as pl
import re
from datetime import datetime

st.set_page_config(
    page_title="Sports Excel Viewer",
    page_icon="🏆",
    layout="wide"
)

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Ice Hockey", "Soccer", "Rugby", "Basketball"])

def process_excel(uploaded_file):
    st.success("Excel file uploaded successfully!")
    st.write("File details:")
    file_details = {"Filename": uploaded_file.name, "FileType": uploaded_file.type, "FileSize": uploaded_file.size}
    st.json(file_details)

if page == "Ice Hockey":
    st.title("🏒 Ice Hockey Excel Upload")
    uploaded_file = st.file_uploader("Upload Excel file for Ice Hockey", type=["xls", "xlsx"])
    if uploaded_file is not None:
        df = pl.read_excel(uploaded_file)
        new_columns = df.head(1).row(0)
        df = df.slice(0)
        df.columns = new_columns
        df = df.with_columns(
            pl.when(
                df["Date"].str.starts_with("Ice Hockey")
            )
            .then(df["Date"])
            .otherwise(None)
            .alias("League")
        ).with_columns(
            pl.col("League").forward_fill()
        )
        df = df.filter(pl.col("Postponed") == "0")
        filter_words = ["Russia.KHL", "Czechia.Extraliga", "Slovakia.Extraliga", "Sweden.SHL","Finland.Liiga","Sweden.SHL","Champions Hockey"]
        df = df.filter(
            pl.col("League").str.contains("|".join(filter_words))  # Use regex to match any of the words
        )
        
        df = df.with_columns(
            pl.col("League")
            .str.replace(r",", "")
            .str.replace(r"(?i)\bweek\b", "")
            .str.replace("Ice Hockey.", "")
            .str.replace("Playoff,", "")
            .str.replace("Playoffs,", "")
            .str.replace("Playout", "")
            .str.strip_chars()
            .map_elements(
                lambda x: re.sub(r'\d+', '', str(x)) if x is not None else None,
                return_dtype=pl.Utf8
            )
            .alias("League")
        )
        df = df.with_columns(
            pl.when(pl.col("AP").is_not_null())  # If "AP" is not null, split and sum its values
            .then(
                pl.col("AP")
                .str.split(":")
                .map_elements(lambda x: sum(int(i) for i in x), return_dtype=pl.Int64)
            )
            .when(pl.col("OT").is_not_null())  # If "OT" is not null, split and sum its values
            .then(
                pl.col("OT")
                .str.split(":")
                .map_elements(lambda x: sum(int(i) for i in x), return_dtype=pl.Int64)
            )
            .when(pl.col("FT").is_not_null())  # If "FT" is not null, split and sum its values
            .then(
                pl.col("FT")
                .str.split(":")
                .map_elements(lambda x: sum(int(i) for i in x), return_dtype=pl.Int64)
            )
            .otherwise(None)  # If all columns are null, set "Goals" to None
            .alias("Goals")  # Name the new column "Goals"
        )

        # Step 10: Create a new column "Period" based on the conditions
        df = df.with_columns(
            pl.when(pl.col("AP").is_not_null())  # If "AP" is not null, set "Period" to 5
            .then(5)
            .when(pl.col("OT").is_not_null())  # If "OT" is not null, set "Period" to 4
            .then(4)
            .otherwise(3)  # Otherwise, set "Period" to 3
            .alias("Period")  # Name the new column "Period"
        )

        # Step 11: Drop specified columns
        columns_to_drop = ["FT", "1", "2", "3", "OT", "AP", "Postponed"]
        df = df.drop(columns_to_drop)

        # Step 12: Add two empty columns after "Match Id"
        df = df.with_columns(
            pl.lit(None).alias("Datapoints"),  # Add empty columns for faster copy and pasting
            pl.lit(None).alias("Issue"), 
            pl.lit(None).alias("Suspensions"),
            pl.lit(None).alias("Suspension issue"),  
            pl.lit(None).alias("Goals issue"),    
        )
        
        # Step 13: Rearrange columns to place the empty columns after "Match Id"
        df_display = df.select(["Date", "KO", "League", "Home", "Away", "Match Id", "Datapoints", "Issue", "Goals","Goals issue","Suspensions","Suspension issue","Period"])
        st.subheader("Processed Ice Hockey Data")
        st.dataframe(df_display)
        current_date = datetime.now().strftime("%Y%m%d")
        # Download button - use df_display instead of df
        output = BytesIO()
        df_display.write_excel(output)  # Write the displayed columns only
        output.seek(0)
        st.download_button(
            label="Download Excel",
            data=output,
            file_name=f"Ice Hockey - {current_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

elif page == "Soccer":
    st.title("⚽ Soccer Excel Upload")
    uploaded_file = st.file_uploader("Upload Excel file for Soccer", type=["xls", "xlsx"])
    if uploaded_file is not None:
        try:
            df = pl.read_excel(uploaded_file)
            new_columns = df.head(1).row(0)
            df = df.slice(0)
            df.columns = new_columns
            df = df.with_columns(
                pl.when(
                    df["Date"].str.starts_with("Soccer")
                )
                .then(df["Date"])
                .otherwise(None)
                .alias("League")
            ).with_columns(
                pl.col("League").forward_fill()
            )
            df = df.filter(pl.col("Postponed") == "0")
            filter_words = ["Italy.Serie A", "Spain.LaLiga", "England.Premier League", "Germany.Bundesliga", "USA.Major League Soccer","Austra.Bundesliga"]
            df = df.filter(
                pl.col("League").str.contains("|".join(filter_words))
            )
            df = df.with_columns(
                pl.col("League")
                .str.replace(r",", "")
                .str.replace(r"(?i)\bweek\b", "")
                .str.replace("Soccer.", "")
                .str.strip_chars()
                .map_elements(
                    lambda x: re.sub(r'\d+', '', str(x)) if x is not None else None,
                    return_dtype=pl.Utf8
                )
                .alias("League")
            )
            # Filter out rows where League column contains "women" (case insensitive)
            if "League" in df.columns:
                df = df.filter(
                    ~pl.col("League").str.to_lowercase().str.contains("women")
                )
            columns_to_drop = ["AP","OT","HT","FT","Comment", "Postponed"]
            df = df.drop(columns_to_drop)
            if "Date" in df.columns:
                df = df.with_columns(
                    pl.col("Date").str.strptime(pl.Date, format="%d/%m %y")
                            .dt.strftime("%m/%d/%Y")
                            .alias("Date")
                )
            st.subheader("Processed League Data")
            df_display = df.select([
                "Date", "KO", "League", "Home", "Away", "Match Id"
            ])
            
            st.dataframe(df_display)
            current_date = datetime.now().strftime("%Y%m%d")
            
            # Download button - use df_display instead of df
            output = BytesIO()
            df_display.write_excel(output)  # Write the displayed columns only
            output.seek(0)
            st.download_button(
                label="Download Excel",
                data=output,
                file_name=f"League Data - {current_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
                

elif page == "Rugby":
    st.title("🏉 Rugby Excel Upload")
    uploaded_file = st.file_uploader("Upload Excel file for Rugby", type=["xls", "xlsx"])
    if uploaded_file is not None:
        try:
            df = pl.read_excel(uploaded_file)
            new_columns = df.head(1).row(0)
            df = df.slice(0)
            df.columns = new_columns
            df = df.with_columns(
                pl.when(
                    df["Date"].str.starts_with("Rugby")
                )
                .then(df["Date"])
                .otherwise(None)
                .alias("League")
            ).with_columns(
                pl.col("League").forward_fill()
            )
            df = df.filter(pl.col("Postponed") == "0")
            filter_words = ["Six Nations", "Super Rugby", "Premiership Rugby"]
            df = df.filter(
                pl.col("League").str.contains("|".join(filter_words))
            )
            df = df.with_columns(
                pl.col("League")
                .str.replace(r",", "")
                .str.replace(r"(?i)\bweek\b", "")
                .str.replace("Rugby.", "")
                .str.strip_chars()
                .map_elements(
                    lambda x: re.sub(r'\d+', '', str(x)) if x is not None else None,
                    return_dtype=pl.Utf8
                )
                .alias("League")
            )
            # Filter out rows where League column contains "women" (case insensitive)
            if "League" in df.columns:
                df = df.filter(
                    ~pl.col("League").str.to_lowercase().str.contains("women")
                )
            columns_to_drop = ["AP","OT","HT","FT","Comment", "Postponed"]
            df = df.drop(columns_to_drop)
            if "Date" in df.columns:
                df = df.with_columns(
                    pl.col("Date").str.strptime(pl.Date, format="%d/%m %y")
                            .dt.strftime("%m/%d/%Y")
                            .alias("Date")
                )
            st.subheader("Processed League Data")
            df_display = df.select([
                "Date", "KO", "League", "Home", "Away", "Match Id"
            ])
            
            st.dataframe(df_display)
            current_date = datetime.now().strftime("%Y%m%d")
            
            # Download button - use df_display instead of df
            output = BytesIO()
            df_display.write_excel(output)  # Write the displayed columns only
            output.seek(0)
            st.download_button(
                label="Download Excel",
                data=output,
                file_name=f"League Data - {current_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

elif page == "Basketball":
    st.title("🏀 Basketball Excel Upload")
    uploaded_file = st.file_uploader("Upload Excel file for Basketball", type=["xls", "xlsx"])
    if uploaded_file is not None:
        process_excel(uploaded_file)
