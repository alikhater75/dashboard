# src/edit_projects.py

import streamlit as st
import pandas as pd
import asyncio

from .api_client import (
    get_portfolios, get_projects, get_group_activities,
    add_portfolio, update_portfolio, delete_portfolio,
    add_project, update_project, delete_project,
    add_group_activity, update_group_activity, delete_group_activity
)

def enrich_activity_df(df, project_name_to_id, project_id_to_portfolio, project_names):
    df = df.copy()  # Avoid modifying the original dataframe

    df.rename(columns={
        'project': 'project_name',
        'Project': 'project_name',
        'portfolio': 'portfolio_name',
        'Portfolio': 'portfolio_name'
    }, inplace=True)

    for col in ['Project', 'Portfolio', 'project', 'portfolio']:
        if col in df.columns:
            df.drop(columns=[col], inplace=True)

    df['id'] = pd.to_numeric(df.get('id', pd.NA), errors='coerce').astype('Int64')
    df['project_name'] = df.get('project_name', '').apply(lambda x: x if x in project_names else project_names[0])
    df['project_id'] = df['project_name'].map(project_name_to_id)
    df['portfolio_name'] = df['project_id'].map(project_id_to_portfolio)

    return df


# --- Main Page Rendering ---

def show_edit_projects_page():
    """Renders the main page and handles tab navigation."""
    st.header("Manage Projects, Portfolios, and Activities")

    if 'confirm_delete' in st.session_state:
        render_confirmation_dialog()
    else:
        tab1, tab2, tab3 = st.tabs(["Portfolios", "Projects", "Group Activities"])
        with tab1:
            render_portfolios_tab()
        with tab2:
            render_projects_tab()
        with tab3:
            render_activities_tab()

# --- UI Rendering Functions ---

def render_portfolios_tab():
    """Manages the UI for the Portfolios tab."""
    st.subheader("Manage Portfolios")
    try:
        original_data = asyncio.run(get_portfolios())
        df = pd.DataFrame(original_data)

        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={"id": None},
            key="portfolio_editor"
        )

        if st.button("Save Portfolio Changes"):
            with st.spinner("Saving..."):
                asyncio.run(process_generic_changes(df, edited_df, item_type='portfolio'))
            st.rerun()

    except Exception as e:
        st.error(f"Failed to load portfolios: {e}")

def render_projects_tab():
    """Manages the UI for the Projects tab."""
    st.subheader("Manage Projects")
    try:
        projects_data = asyncio.run(get_projects())
        portfolios_data = asyncio.run(get_portfolios())

        df = pd.DataFrame(projects_data)
        portfolio_map = {p['name']: p['id'] for p in portfolios_data}

        edited_df = st.data_editor(
            df.copy(),
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "id": None,
                "project_name": "Project Name",
                "portfolio_name": st.column_config.SelectboxColumn("Portfolio", options=list(portfolio_map.keys()), required=True),
                "portfolio_id": None
            },
            key="project_editor"
        )

        if st.button("Save Project Changes"):
            edited_df['portfolio_id'] = edited_df['portfolio_name'].map(portfolio_map)
            with st.spinner("Saving..."):
                asyncio.run(process_generic_changes(df, edited_df, item_type='project'))
            st.rerun()

    except Exception as e:
        st.error(f"Failed to load projects: {e}")


def render_activities_tab():
    """Manages the UI for the Group Activities tab with controlled form-based entry and readonly table."""
    st.subheader("Manage Group Activities")

    try:
        activities_data = asyncio.run(get_group_activities())
        projects_data = asyncio.run(get_projects())

        if not projects_data:
            st.warning("Cannot manage activities because no projects exist. Please add a project first.")
            return

        project_name_to_id = {p['project_name']: p['id'] for p in projects_data}
        project_id_to_portfolio = {p['id']: p['portfolio_name'] for p in projects_data}
        project_names = list(project_name_to_id.keys())

        df = pd.DataFrame(activities_data)
        df = enrich_activity_df(
            pd.DataFrame(activities_data),
            project_name_to_id,
            project_id_to_portfolio,
            project_names
        )

        if 'activity_df' not in st.session_state:
            st.session_state.original_activity_df = df.copy()
            st.session_state.activity_df = df.copy()

        # Add new activity
        st.markdown("### ➕ Add New Group Activity")
        selected_project = st.selectbox("Project", project_names, key="new_activity_project")
        selected_project_id = project_name_to_id[selected_project]
        selected_portfolio = project_id_to_portfolio[selected_project_id]

        with st.form("add_group_activity_form", clear_on_submit=True):
            new_activity_name = st.text_input("Activity Name")
            st.text_input("Portfolio", value=selected_portfolio, disabled=True)

            submitted = st.form_submit_button("Add Activity")
            existing_ids = st.session_state.activity_df['id'].dropna()
            next_id = existing_ids.max() + 1 if not existing_ids.empty else 1
            if submitted:
                new_row = {
                    "id": int(next_id),
                    "name": new_activity_name,
                    "project_name": selected_project,
                    "portfolio_name": selected_portfolio,
                    "project_id": selected_project_id,
                }
                st.session_state.activity_df = pd.concat(
                    [st.session_state.activity_df, pd.DataFrame([new_row])],
                    ignore_index=True
                )
                st.success(f"Added activity '{new_activity_name}' ➕")

        # Show existing activities
        st.markdown("### 📝 Current Group Activities")
        edited_activity_df = st.data_editor(
            st.session_state.activity_df,
            use_container_width=True,
            disabled=False,
            num_rows="dynamic",
            column_config={
                "id": None,
                "name": "Activity Name",
                "project_name": st.column_config.SelectboxColumn("Project", options=project_names, required=True),
                "portfolio_name": st.column_config.TextColumn("Portfolio", disabled=True),
                "project_id": None,
            },
            key="readonly_activity_editor"
        )

        if st.button("Save Activity Changes"):
            with st.spinner("Saving..."):
                asyncio.run(process_generic_changes(
                    st.session_state.original_activity_df,
                    edited_activity_df,
                    item_type='activity'
                ))
            refreshed_df = pd.DataFrame(asyncio.run(get_group_activities()))
            refreshed_df = enrich_activity_df(refreshed_df, project_name_to_id, project_id_to_portfolio, project_names)

            st.session_state.original_activity_df = refreshed_df.copy()
            st.session_state.activity_df = refreshed_df.copy()

            st.success("Changes saved and memory refreshed ✅")
            st.rerun()

    except Exception as e:
        st.error(f"An error occurred: {e}")

def render_confirmation_dialog():
    """Displays a modal dialog to confirm a delete action."""
    item_info = st.session_state.get('confirm_delete', {})

    with st.container(border=True):
        st.error(f"⚠️ Are you sure you want to permanently delete **{item_info['name']}**?")
        col1, col2 = st.columns(2)

        if col1.button("Yes, delete it", type="primary", use_container_width=True):
            actions = {'portfolio': delete_portfolio, 'project': delete_project, 'activity': delete_group_activity}
            try:
                with st.spinner("Deleting..."):
                    asyncio.run(actions[item_info['type']](item_info['id']))
                st.toast(f"Deleted '{item_info['name']}'", icon="🗑️")
            except Exception as e:
                print(f"Error deleting {item_info['type']}: {e}")
                st.error(f"Deletion failed: {e}")

            del st.session_state['confirm_delete']
            st.rerun()

        if col2.button("Cancel", use_container_width=True):
            del st.session_state['confirm_delete']
            st.rerun()

async def process_activity_additions(original_df, edited_df):
    """
    Correctly identifies and saves ONLY new activities by comparing the edited
    DataFrame against the original state from the database.
    """
    # Find rows that exist in the edited_df but not in the original_df
    # We use a merge with an indicator to reliably find new rows.
    merged_df = edited_df.merge(original_df, on=['name', 'project_id'], how='left', indicator=True)
    new_rows = merged_df[merged_df['_merge'] == 'left_only']
    
    if new_rows.empty:
        st.toast("No new activities to save.", icon="🤷‍♀️")
        return

    tasks = []
    for _, row in new_rows.iterrows():
        payload = {'name': row['name'], 'project_id': int(row['project_id'])}
        tasks.append(add_group_activity(**payload))
        st.toast(f"Saving '{payload['name']}'...", icon="➕")

    if tasks:
        await asyncio.gather(*tasks)
        
async def process_generic_changes(original_df, edited_df, item_type):
    """A single, robust function to handle all async CRUD logic for tabs that support full editing."""

    config = {
        'portfolio': {
            'add': add_portfolio,
            'update': update_portfolio,
            'name_col': 'name'
        },
        'project': {
            'add': add_project,
            'update': update_project,
            'name_col': 'project_name'
        },
        'activity': {
            'add': add_group_activity,
            'update': update_group_activity,
            'name_col': 'name'
        }
    }

    if item_type not in config:
        raise ValueError(f"Unsupported item type: {item_type}")

    original_df_copy = original_df.copy()
    edited_df_copy = edited_df.copy()


    print("****"*20)
    print(original_df_copy)
    print("------"*20)
    print(edited_df_copy)
    print("****"*20)


    # Normalize ID columns
    original_df_copy['id'] = pd.to_numeric(original_df_copy['id'], errors='coerce').astype('Int64')
    edited_df_copy['id'] = pd.to_numeric(edited_df_copy['id'], errors='coerce').astype('Int64')


    # Ensure 'id' exists in both
    if 'id' not in original_df_copy.columns:
        original_df_copy['id'] = pd.NA
    if 'id' not in edited_df_copy.columns:
        edited_df_copy['id'] = pd.NA

    original_ids = set(original_df_copy['id'].dropna())
    edited_ids = set(edited_df_copy['id'].dropna())

    # ----------------------
    # 1. Handle deletion
    # ----------------------
    original_ids = set(original_df_copy['id'].dropna().tolist())
    edited_ids = set(edited_df_copy['id'].dropna().tolist())

    deleted_ids = original_ids - edited_ids
    print(f"Deleted IDs: {deleted_ids}")

    if deleted_ids:
        # Pick first deleted row and send to confirmation
        item_id_to_delete = list(deleted_ids)[0]
        item_to_delete = original_df_copy[original_df_copy['id'] == item_id_to_delete].iloc[0]

        st.session_state['confirm_delete'] = {
            'type': item_type,
            'id': int(item_id_to_delete),
            'name': item_to_delete[config[item_type]['name_col']]
        }
        return  # wait for confirmation


    tasks = []

    # ----------------------
    # 2. Handle addition
    # ----------------------

    # Define keys to identify rows — update this if needed
    added_rows = edited_df_copy[~edited_df_copy['id'].isin(original_df_copy['id'])]
    print(f"Added Rows: {added_rows}")
    for _, row in added_rows.iterrows():
        payload = {
            'name': row[config[item_type]['name_col']]
        }
        if item_type == 'project':
            payload['portfolio_id'] = row['portfolio_id']
        elif item_type == 'activity':
            payload['project_id'] = row['project_id']

        tasks.append(config[item_type]['add'](**payload))
        st.toast(f"Added '{payload['name']}'", icon="➕")

    # ----------------------
    # 3. Handle updates
    # ----------------------
    updated_ids = original_df_copy['id'].dropna().isin(edited_df_copy['id']).values
    common_ids = original_df_copy.loc[updated_ids, 'id']


    for id_val in common_ids:
        original_row = original_df_copy.set_index('id').loc[id_val]
        edited_row = edited_df_copy.set_index('id').loc[id_val]

        if not original_row.equals(edited_row):
            id_key = f"{item_type}_id"
            payload = {
                id_key: int(id_val),
                'name': edited_row[config[item_type]['name_col']]
            }

            if item_type == 'project':
                payload['portfolio_id'] = int(edited_row['portfolio_id'])
            elif item_type == 'activity':
                payload['project_id'] = int(edited_row['project_id'])

            print("Updated id:", id_val)
            tasks.append(config[item_type]['update'](**payload))
            st.toast(f"Updated '{payload['name']}'", icon="🔄")

    if tasks:
        await asyncio.gather(*tasks)
