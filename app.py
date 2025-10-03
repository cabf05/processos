# app.py
import streamlit as st
import uuid
import json
from typing import Dict, List

st.set_page_config(page_title="Process Flow Assistant (MVP)", layout="wide")

# -------------------------
# Helper / Model functions
# -------------------------
def generate_id(prefix="n"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def init_process():
    return {
        "name": "New Process",
        "nodes": [
            {"id": "start", "label": "Start", "type": "start"},
        ],
        "edges": []
    }

def find_node(process, node_id):
    for n in process["nodes"]:
        if n["id"] == node_id:
            return n
    return None

def remove_node(process, node_id):
    process["nodes"] = [n for n in process["nodes"] if n["id"] != node_id]
    process["edges"] = [e for e in process["edges"] if e["from"] != node_id and e["to"] != node_id]

def add_node(process, label, ntype="task"):
    nid = generate_id("n")
    process["nodes"].append({"id": nid, "label": label, "type": ntype})
    return nid

def add_edge(process, from_id, to_id, label=None):
    process["edges"].append({"from": from_id, "to": to_id, "label": label})

def update_node_label(process, node_id, new_label):
    node = find_node(process, node_id)
    if node:
        node["label"] = new_label

def node_repr(node):
    t = node["type"]
    if t == "start" or t == "end":
        return f"{node['id']}([{node['label']}])"
    if t == "task":
        return f"{node['id']}[{node['label']}]"
    if t == "decision":
        return f"{node['id']}{{{node['label']}}}"
    # fallback
    return f"{node['id']}[{node['label']}]"

def mermaid_for_edge(e):
    label = f'|{e["label"]}|' if e.get("label") else ""
    return f'{e["from"]} -->{label} {e["to"]}'

def generate_mermaid(process):
    lines = ["flowchart TD"]
    # nodes
    for n in process["nodes"]:
        # ensure labels escape newlines
        safe_label = n["label"].replace("\n", " ")
        if n["type"] == "start" or n["type"] == "end":
            lines.append(f'    {n["id"]}([{safe_label}])')
        elif n["type"] == "task":
            lines.append(f'    {n["id"]}[{safe_label}]')
        elif n["type"] == "decision":
            lines.append(f'    {n["id"]}{{{safe_label}}}')
        else:
            lines.append(f'    {n["id"]}[{safe_label}]')
    # edges
    for e in process["edges"]:
        if e.get("label"):
            # Mermaid: node -->|Label| node2
            lines.append(f'    {e["from"]} -->|{e["label"]}| {e["to"]}')
        else:
            lines.append(f'    {e["from"]} --> {e["to"]}')
    return "\n".join(lines)

# -------------------------
# Session state init
# -------------------------
if "process" not in st.session_state:
    st.session_state.process = init_process()
if "selected_node" not in st.session_state:
    st.session_state.selected_node = "start"

process = st.session_state.process

# -------------------------
# Layout: three columns
# -------------------------
col1, col2, col3 = st.columns([1.2, 1.6, 1.0])

# ---------- Left: Guided questions / builder ----------
with col1:
    st.header("Step-by-step Assistant")
    st.markdown("Answer the questions like a consultant — build your process progressively.")

    # Process name
    pname = st.text_input("Process name", value=process.get("name", "New Process"))
    if pname != process.get("name"):
        process["name"] = pname

    st.subheader("Add first activity / step")
    first_activity = st.text_input("What's the first activity? (leave blank to skip)", key="first_act")
    if st.button("Add first activity"):
        if first_activity.strip():
            nid = add_node(process, first_activity.strip(), ntype="task")
            add_edge(process, "start", nid)
            st.session_state.selected_node = nid
            st.experimental_rerun()
        else:
            st.warning("Type an activity label.")

    st.markdown("---")
    st.subheader("Add a Task (activity)")
    parent_for_task = st.selectbox("Attach task after which node?", options=[(n["id"], n["label"]) for n in process["nodes"]], format_func=lambda x: f"{x[1]} ({x[0]})")
    task_label = st.text_input("Task label", key="task_label")
    if st.button("Add Task"):
        p_id = parent_for_task[0]
        if task_label.strip():
            nid = add_node(process, task_label.strip(), ntype="task")
            add_edge(process, p_id, nid)
            st.session_state.selected_node = nid
            st.experimental_rerun()
        else:
            st.warning("Provide a label for the task.")

    st.markdown("---")
    st.subheader("Add a Decision (Yes/No)")
    parent_for_dec = st.selectbox("Decision after node?", options=[(n["id"], n["label"]) for n in process["nodes"]], key="dec_parent", format_func=lambda x: f"{x[1]} ({x[0]})")
    dec_label = st.text_input("Decision label (e.g., Documents correct?)", key="dec_label")
    yes_label = st.text_input("Label for YES path (activity) (e.g., Proceed)", key="yes_label")
    no_label = st.text_input("Label for NO path (activity) (e.g., Rework)", key="no_label")
    if st.button("Add Decision"):
        if not dec_label.strip():
            st.warning("Decision needs a label.")
        else:
            dec_id = add_node(process, dec_label.strip(), ntype="decision")
            add_edge(process, parent_for_dec[0], dec_id)
            # add yes node
            if yes_label.strip():
                yes_id = add_node(process, yes_label.strip(), ntype="task")
                add_edge(process, dec_id, yes_id, label="Yes")
            else:
                # create an unnamed task node
                yes_id = add_node(process, "Yes path", ntype="task")
                add_edge(process, dec_id, yes_id, label="Yes")
            # add no node
            if no_label.strip():
                no_id = add_node(process, no_label.strip(), ntype="task")
                add_edge(process, dec_id, no_id, label="No")
            else:
                no_id = add_node(process, "No path", ntype="task")
                add_edge(process, dec_id, no_id, label="No")
            st.session_state.selected_node = dec_id
            st.experimental_rerun()

    st.markdown("---")
    st.subheader("End / Close a path")
    attach_to = st.selectbox("Attach End after which node?", options=[(n["id"], n["label"]) for n in process["nodes"]], key="end_parent", format_func=lambda x: f"{x[1]} ({x[0]})")
    if st.button("Add End"):
        # add or use existing end node id
        # check if an 'end' node already exists
        end_nodes = [n for n in process["nodes"] if n["type"] == "end"]
        if end_nodes:
            end_id = end_nodes[0]["id"]
        else:
            end_id = "end"
            # ensure unique id if "end" taken
            if find_node(process, end_id):
                end_id = add_node(process, "End", ntype="end")
            else:
                process["nodes"].append({"id": end_id, "label": "End", "type": "end"})
        add_edge(process, attach_to[0], end_id)
        st.experimental_rerun()

    st.markdown("---")
    st.subheader("Quick actions")
    if st.button("Reset process"):
        st.session_state.process = init_process()
        st.experimental_rerun()

    st.caption("Tip: Use the right panel to edit or remove existing nodes and edges.")

# ---------- Center: Diagram ----------
with col2:
    st.header("Diagram (live preview)")
    mermaid_code = generate_mermaid(process)
    st.code(mermaid_code, language="mermaid")

    # Render mermaid via HTML -> using mermaid CDN
    mermaid_html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
      <style>
        body {{ margin: 0; padding: 0; }}
      </style>
    </head>
    <body>
      <div class="mermaid">
{mermaid_code}
      </div>
      <script>
        mermaid.initialize({{startOnLoad:true}});
      </script>
    </body>
    </html>
    """
    st.components.v1.html(mermaid_html, height=520, scrolling=True)

    st.markdown("---")
    st.subheader("Export / Download")
    st.download_button("Download process as JSON", data=json.dumps(process, indent=2), file_name=f"{process.get('name','process')}.json", mime="application/json")
    st.download_button("Download Mermaid text", data=mermaid_code, file_name=f"{process.get('name','process')}.mmd", mime="text/plain")

    st.info("If you want image export (PNG/SVG), you can copy the Mermaid text and use mermaid.live or mermaid-cli to render images.")

# ---------- Right: Edit nodes & edges ----------
with col3:
    st.header("Nodes & Edges (edit)")
    st.markdown("Select a node to edit its label or delete it. Edges update automatically.")

    node_ids = [n["id"] for n in process["nodes"]]
    selected_node = st.selectbox("Selected node", options=node_ids, format_func=lambda x: f"{find_node(process,x)['label']} ({x})")
    st.session_state.selected_node = selected_node

    node_obj = find_node(process, selected_node)
    if node_obj:
        st.markdown(f"**Type:** {node_obj['type']}")
        new_label = st.text_input("Edit label", value=node_obj["label"], key=f"edit_{selected_node}")
        if st.button("Save label", key=f"save_{selected_node}"):
            update_node_label(process, selected_node, new_label)
            st.experimental_rerun()

        if node_obj["type"] not in ["start", "end"]:
            if st.button("Delete node", key=f"del_{selected_node}"):
                remove_node(process, selected_node)
                st.experimental_rerun()
        else:
            st.caption("Start/End nodes cannot be deleted from this UI (but you can reset the whole process).")

    st.markdown("---")
    st.subheader("Edges")
    if process["edges"]:
        for idx, e in enumerate(process["edges"]):
            from_label = find_node(process, e["from"])["label"] if find_node(process, e["from"]) else e["from"]
            to_label = find_node(process, e["to"])["label"] if find_node(process, e["to"]) else e["to"]
            col_a, col_b = st.columns([0.8, 0.2])
            with col_a:
                st.write(f"{from_label} → {to_label} " + (f" (label: {e['label']})" if e.get("label") else ""))
            with col_b:
                if st.button("Delete", key=f"del_edge_{idx}"):
                    process["edges"].pop(idx)
                    st.experimental_rerun()
    else:
        st.write("No edges yet.")

    st.markdown("---")
    st.subheader("Save / Load process file")
    uploaded = st.file_uploader("Upload process JSON", type=["json"])
    if uploaded is not None:
        try:
            content = json.load(uploaded)
            # minimal validation
            if "nodes" in content and "edges" in content:
                st.session_state.process = content
                st.success("Process loaded.")
                st.experimental_rerun()
            else:
                st.error("Invalid process JSON (missing nodes/edges).")
        except Exception as ex:
            st.error(f"Error reading file: {ex}")

    st.caption("You can also copy/paste the Mermaid code from the preview to external renderers.")

# -------------------------
# Footer: small tips
# -------------------------
st.markdown("---")
st.markdown(
    """
    **How to extend this MVP (ideas):**
    - Allow multi-option decisions (not only Yes/No).
    - Let users re-wire edges (drag & drop) in a GUI.
    - Add user permissions and save templates.
    - Export to PNG/SVG via server-side rendering (mermaid-cli) or headless browser.
    - Add automatic step validation (e.g., required approvals, SLA times).
    """
)
