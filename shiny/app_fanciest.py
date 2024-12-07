from shiny import App, render, ui, reactive
from shinywidgets import render_altair, output_widget
import pandas as pd
import json
import altair as alt
import geopandas as gpd

# Import turnout rate data
df2012 = pd.read_csv('data/df2012_clean.csv')
df2016 = pd.read_csv('data/df2016_clean.csv')
df2020 = pd.read_csv('data/df2020_clean.csv')
df2024 = pd.read_csv('data/df2024_clean.csv')

# Import geodata
geodata = gpd.read_file('data/gz_2010_us_040_00_500k/gz_2010_us_040_00_500k.shp')

# Define swing states for each year
swing_states = {
    "2012": ["Florida", "Ohio", "Virginia", "Colorado", "Iowa", "New Hampshire", "Nevada", "North Carolina"],
    "2016": ["Florida", "Ohio", "Pennsylvania", "Michigan", "Wisconsin", "North Carolina", "Arizona", "Nevada"],
    "2020": ["Arizona", "Georgia", "Michigan", "Nevada", "North Carolina", "Pennsylvania", "Wisconsin"],
    "2024": ["Arizona", "Georgia", "Michigan", "Nevada", "North Carolina", "Pennsylvania", "Wisconsin"]
}

### UI
app_ui = ui.page_fluid(
    ui.h2("VEP Turnout Rate by State"),
    ui.layout_columns(
        ui.card(
            ui.card_header("Turnout Rate Map"),
            ui.input_select(
                id="year_select",
                label="Select Year:",
                choices=["2012", "2016", "2020", "2024"],  
                selected="2012"
            ),
            ui.input_checkbox(
                id="toggle_relative",  # checkbox switch
                label="Show Relative Values", 
                value=True  # Default to relative values
            ),
            ui.input_switch(
                id="toggle_swing",  # Toggle switch for swing states
                label="Show Only Swing States", 
                value=False  # Default to showing all states
            ),
            output_widget("state_map"),
            full_screen=True
        ),
        ui.card(
            ui.card_header("Selected Data"),
            ui.output_data_frame("data_table"),  # Use output_data_frame for rendering the table
            full_screen=True
        )
    )
)

### SERVER
def server(input, output, session):
    @reactive.Calc
    def selected_year_data():
        year = input.year_select()
        if year == "2012":
            return df2012
        elif year == "2016":
            return df2016
        elif year == "2020":
            return df2020
        elif year == "2024":
            return df2024

    @reactive.Calc
    def is_relative():
        return input.toggle_relative()

    @reactive.Calc
    def filtered_data():
        # Get the selected year and whether to show only swing states
        year = input.year_select()
        year_data = selected_year_data()
        is_swing_only = input.toggle_swing()

        # Merge geodata and year data
        merged = geodata.merge(year_data, on="NAME", how="left")

        # Filter to show only swing states if toggle is active
        if is_swing_only:
            swing_state_list = swing_states[year]
            merged = merged[merged["NAME"].isin(swing_state_list)]

        return merged

    @output
    @render_altair
    def state_map():
        # Get filtered data
        merged = filtered_data()

        # Convert merged GeoDataFrame to GeoJSON
        merged_json = json.loads(merged.to_json())

        # Determine which column to use for the map
        column_to_use = "VEP_relative" if is_relative() else "VEP"
        color_scale = (
            alt.Scale(domain=[-20, 0, 20], range=["blue", "white", "red"])
            if is_relative()
            else alt.Scale(domain=[40, 80], scheme="blues")
        )
        color_title = "Relative Turnout Rate (%)" if is_relative() else "Turnout Rate (%)"

        # Draw Altair map
        chart = alt.Chart(alt.Data(values=merged_json['features'])).mark_geoshape().encode(
            color=alt.Color(
                f'properties.{column_to_use}:Q',
                scale=color_scale,
                title=color_title
            ),
            tooltip=[
                alt.Tooltip('properties.NAME:N', title='State'),
                alt.Tooltip(f'properties.{column_to_use}:Q', title=color_title)
            ]
        ).properties(
            title=f"VEP Turnout Rate by State in {input.year_select()}",
            width=600,
            height=400
        ).project('albersUsa')

        return chart

    @output
    @render.data_frame
    def data_table():
        # Get the data for the selected year
        year_data = selected_year_data()

        # Return the filtered DataFrame
        return year_data

app = App(app_ui, server)
