# app.py
import streamlit as st
import uuid
import json
from typing import Optional

st.set_page_config(page_title="Assistente de Processos (MVP)", layout="wide")

# -------------------
# Helpers / Modelo
# -------------------
def generate_id(prefix="n"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def init_process():
    return {
        "id": generate_id("proc"),
        "name": "Novo Processo",
        "nodes": [
            {"id": "start", "label": "Início", "type": "start"},
        ],
        "edges": []
    }

def find_node(process, node_id):
    for n in process["nodes"]:
        if n["id"] == node_id:
            return n
    return None

def get_node_index(process, node_id) -> Optional[int]:
    for i, n in enumerate(process["nodes"]):
        if n["id"] == node_id:
            return i
    return None

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

def delete_nodes_after(process, node_id):
    """
    Remove nodes that were added *após* node_id in creation order (list order).
    Also remove edges that reference deleted nodes.
    """
    idx = get_node_index(process, node_id)
    if idx is None:
        return
    # Keep nodes up to idx (inclusive)
    keep = process["nodes"][: idx + 1]
    removed = process["nodes"][idx + 1 :]
    removed_ids = {n["id"] for n in removed}
    process["nodes"] = keep
    # Remove edges that reference removed nodes
    process["edges"] = [e for e in process["edges"] if e["from"] not in removed_ids and e["to"] not in removed_ids]

def remove_node(process, node_id):
    # Remove a single node and its edges
    process["nodes"] = [n for n in process["nodes"] if n["id"] != node_id]
    process["edges"] = [e for e in process["edges"] if e["from"] != node_id and e["to"] != node_id]

def ensure_end_node(process):
    end_nodes = [n for n in process["nodes"] if n["type"] == "end"]
    if end_nodes:
        return end_nodes[0]["id"]
    # create end node
    end_id = "end"
    # if id in use, create unique
    if find_node(process, end_id):
        end_id = add_node(process, "Fim", ntype="end")
    else:
        process["nodes"].append({"id": end_id, "label": "Fim", "type": "end"})
    return end_id

def generate_mermaid(process):
    lines = ["flowchart TD"]
    # nodes
    for n in process["nodes"]:
        safe_label = n["label"].replace("\n", " ")
        if n["type"] in ("start", "end"):
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
            lines.append(f'    {e["from"]} -->|{e["label"]}| {e["to"]}')
        else:
            lines.append(f'    {e["from"]} --> {e["to"]}')
    return "\n".join(lines)

def last_non_start_node(process):
    # return the last node that is not the start, else start
    if len(process["nodes"]) == 1:
        return process["nodes"][0]["id"]
    else:
        return process["nodes"][-1]["id"]

# -------------------
# Session state init
# -------------------
if "process" not in st.session_state:
    st.session_state.process = init_process()
if "conversation" not in st.session_state:
    st.session_state.conversation = []  # list of dicts {role, text}
if "expecting" not in st.session_state:
    # expecting: None or one of: "process_name", "first_activity", "next_action"
    st.session_state.expecting = "process_name"
if "last_added_node" not in st.session_state:
    st.session_state.last_added_node = None

process = st.session_state.process

# -------------------
# Conversation helpers
# -------------------
def assistant_say(text):
    st.session_state.conversation.append({"role": "assistant", "text": text})

def user_say(text):
    st.session_state.conversation.append({"role": "user", "text": text})

# initialize greeting if conversation empty
if not st.session_state.conversation:
    assistant_say("Olá! Sou seu assistente para criar processos. Vamos começar.")
    assistant_say("Qual o nome do processo?")
    st.session_state.expecting = "process_name"

# -------------------
# Layout
# -------------------
col_left, col_right = st.columns([3.4, 1])

with col_left:
    st.title("Assistente de Processos — MVP")
    st.markdown("À esquerda: diagrama do processo. À direita: 'chat' com o assistente.")

    # Top controls: nome do processo e ações gerais
    st.subheader("Visão geral")
    nome = st.text_input("Nome do processo", value=process.get("name", "Novo Processo"))
    if nome != process.get("name"):
        process["name"] = nome

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("Salvar JSON (download)"):
            st.download_button("Clique para baixar JSON", data=json.dumps(process, indent=2, ensure_ascii=False), file_name=f"{process.get('name','process')}.json", mime="application/json")
    with c2:
        if st.button("Exportar Mermaid (mostrar)"):
            st.info("Copie o texto Mermaid abaixo e cole em mermaid.live ou outro renderizador.")
            st.code(generate_mermaid(process), language="mermaid")
    with c3:
        if st.button("Resetar processo"):
            st.session_state.process = init_process()
            st.session_state.conversation = []
            st.session_state.expecting = "process_name"
            st.session_state.last_added_node = None
            assistant_say("Processo reiniciado.")
            assistant_say("Qual o nome do processo?")

    st.markdown("---")

    # Diagram
    st.subheader("Diagrama (pré-visualização)")
    mermaid_code = generate_mermaid(process)
    st.code(mermaid_code, language="mermaid")

    mermaid_html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
      <style> body {{ margin: 0; padding: 0; }} </style>
    </head>
    <body>
      <div class="mermaid">
{mermaid_code}
      </div>
      <script> mermaid.initialize({{startOnLoad:true}}); </script>
    </body>
    </html>
    """
    st.components.v1.html(mermaid_html, height=520, scrolling=True)

    st.markdown("---")
    st.subheader("Estrutura do processo (nós e ligações)")
    st.markdown("Atenção: para editar um passo anterior, você precisa apagar todos os passos posteriores (regra do MVP).")
    # List nodes with index and simple controls
    for i, node in enumerate(process["nodes"]):
        cols = st.columns([0.7, 2, 0.6])
        with cols[0]:
            st.write(f"**{i}**")
        with cols[1]:
            st.write(f"**{node['label']}** — _{node['type']}_")
        with cols[2]:
            # Edit action: allowed only if node is last or you delete posterior steps first
            if st.button(f"Editar {i}", key=f"edit_{node['id']}"):
                # check if node is last
                if i != len(process["nodes"]) - 1:
                    st.warning("Para editar este passo você precisa primeiro apagar os passos posteriores. Use 'Deletar até aqui' no chat à direita.")
                else:
                    # show a small modal-like inline edit (use st.session_state temporary storage)
                    st.session_state._editing_node = node["id"]
            if st.button(f"Deletar {i}", key=f"delnode_{node['id']}"):
                # check must not delete start
                if node["type"] == "start":
                    st.error("Não é possível deletar o nó inicial.")
                else:
                    remove_node(process, node["id"])
                    st.success(f"Nó '{node['label']}' removido.")
                    # record in conversation
                    user_say(f"Deletei o passo {i} ({node['label']}).")

    st.markdown("---")
    st.subheader("Arestas")
    if process["edges"]:
        for idx, e in enumerate(process["edges"]):
            from_label = find_node(process, e["from"])["label"] if find_node(process, e["from"]) else e["from"]
            to_label = find_node(process, e["to"])["label"] if find_node(process, e["to"]) else e["to"]
            st.write(f"- {from_label} → {to_label}" + (f" (rótulo: {e['label']})" if e.get("label") else ""))
    else:
        st.write("_Sem arestas ainda_.")

with col_right:
    # Chat-like box
    st.markdown("### Assistente (chat)")
    # simple chat bubble CSS
    st.markdown(
        """
        <style>
        .chat-box { max-height: 540px; overflow:auto; padding:10px; border:1px solid #eee; border-radius:8px; background:#fafafa;}
        .msg-assistant { background:#f1f5f9; padding:8px 12px; border-radius:12px; margin:6px 0; }
        .msg-user { background:#dbeafe; padding:8px 12px; border-radius:12px; margin:6px 0; text-align:right; }
        .small-muted { color: #666; font-size:12px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # conversation box
    chat_container = st.container()
    with chat_container:
        st.write("", unsafe_allow_html=True)
        st.markdown('<div class="chat-box">', unsafe_allow_html=True)
        for m in st.session_state.conversation:
            if m["role"] == "assistant":
                st.markdown(f'<div class="msg-assistant"><strong>Assistente:</strong><div>{m["text"]}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="msg-user"><strong>Você:</strong><div>{m["text"]}</div></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Ações rápidas**")
    # Action selector
    action = st.selectbox("Escolha uma ação", options=[
        "Adicionar tarefa",
        "Adicionar decisão (Sim/Não)",
        "Encerrar processo",
        "Editar passo (regras de exclusão aplicam)",
        "Deletar até um passo (manter este e remover posteriores)",
        "Carregar processo (JSON)",
        "Cancelar / Nenhuma"
    ])

    # Handle each action with dynamic inputs
    if action == "Adicionar tarefa":
        st.markdown("Adiciona uma tarefa **após** o nó selecionado (por padrão o último).")
        parent_options = [(n["id"], f'{n["label"]} ({n["type"]})') for n in process["nodes"]]
        parent_sel = st.selectbox("Anexar após:", options=parent_options, format_func=lambda x: x[1], index=len(parent_options)-1)
        task_label = st.text_input("Rótulo da tarefa", key="task_label")
        if st.button("Adicionar tarefa"):
            if not task_label.strip():
                st.warning("Digite um rótulo para a tarefa.")
            else:
                parent_id = parent_sel[0]
                nid = add_node(process, task_label.strip(), ntype="task")
                add_edge(process, parent_id, nid)
                st.success(f"Tarefa '{task_label}' adicionada após '{find_node(process,parent_id)['label']}'.")
                user_say(f"Adicionar tarefa: {task_label} (após {find_node(process,parent_id)['label']})")
                st.session_state.last_added_node = nid

    elif action == "Adicionar decisão (Sim/Não)":
        st.markdown("Cria um nó de decisão e dois ramos (Sim / Não). Você pode editar ou estender os ramos depois.")
        parent_options = [(n["id"], f'{n["label"]} ({n["type"]})') for n in process["nodes"]]
        parent_sel = st.selectbox("Anexar decisão após:", options=parent_options, format_func=lambda x: x[1], index=len(parent_options)-1, key="dec_parent")
        dec_label = st.text_input("Texto da decisão (ex: Documentos corretos?)", key="dec_label")
        yes_label = st.text_input("Rótulo para caminho 'Sim' (atividade)", key="yes_label", value="Aprovado")
        no_label = st.text_input("Rótulo para caminho 'Não' (atividade)", key="no_label", value="Rejeitado")
        if st.button("Adicionar decisão"):
            if not dec_label.strip():
                st.warning("A decisão precisa de um rótulo.")
            else:
                parent_id = parent_sel[0]
                dec_id = add_node(process, dec_label.strip(), ntype="decision")
                add_edge(process, parent_id, dec_id)
                yes_id = add_node(process, yes_label.strip() or "Sim path", ntype="task")
                no_id = add_node(process, no_label.strip() or "Não path", ntype="task")
                add_edge(process, dec_id, yes_id, label="Sim")
                add_edge(process, dec_id, no_id, label="Não")
                st.success("Decisão adicionada com dois ramos (Sim/Não).")
                user_say(f"Adicionar decisão: {dec_label} (Sim->{yes_label} / Não->{no_label})")
                st.session_state.last_added_node = dec_id

    elif action == "Encerrar processo":
        st.markdown("Anexa um nó 'Fim' após o nó escolhido.")
        parent_options = [(n["id"], f'{n["label"]} ({n["type"]})') for n in process["nodes"]]
        parent_sel = st.selectbox("Anexar fim após:", options=parent_options, format_func=lambda x: x[1], index=len(parent_options)-1, key="end_parent")
        if st.button("Adicionar Fim"):
            parent_id = parent_sel[0]
            end_id = ensure_end_node(process)
            add_edge(process, parent_id, end_id)
            st.success("Caminho encerrado (vinculado ao Fim).")
            user_say(f"Encerrar processo após {find_node(process,parent_id)['label']}")

    elif action == "Editar passo (regras de exclusão aplicam)":
        st.markdown("Você só pode editar um passo se ele for o último; caso contrário, apague os passos posteriores primeiro.")
        node_options = [(n["id"], f'{idx} — {n["label"]} ({n["type"]})') for idx, n in enumerate(process["nodes"])]
        sel = st.selectbox("Selecione o passo a editar", options=node_options, format_func=lambda x: x[1])
        sel_id = sel[0]
        sel_idx = get_node_index(process, sel_id)
        st.write(f"Selecionado: índice {sel_idx} — {find_node(process, sel_id)['label']}")
        new_label = st.text_input("Novo rótulo", value=find_node(process, sel_id)["label"], key="edit_input")
        if st.button("Salvar edição"):
            # check if it's last node
            if sel_idx != len(process["nodes"]) - 1:
                st.error("Para editar este passo você precisa primeiro apagar os passos posteriores (use 'Deletar até um passo').")
            else:
                update_node_label(process, sel_id, new_label.strip() or find_node(process, sel_id)["label"])
                st.success("Rótulo atualizado.")
                user_say(f"Editei passo {sel_idx} -> {new_label.strip()}")

    elif action == "Deletar até um passo (manter este e remover posteriores)":
        st.markdown("Escolha um passo que deseja manter; todos os passos posteriores serão apagados.")
        node_options = [(n["id"], f'{idx} — {n["label"]} ({n["type"]})') for idx, n in enumerate(process["nodes"])]
        sel = st.selectbox("Manter passo (os posteriores serão removidos):", options=node_options, format_func=lambda x: x[1])
        sel_id = sel[0]
        sel_idx = get_node_index(process, sel_id)
        st.write(f"Irá manter o passo {sel_idx} — {find_node(process, sel_id)['label']}")
        if st.button("Deletar posteriores"):
            if sel_idx == len(process["nodes"]) - 1:
                st.info("Não há passos posteriores para deletar.")
            else:
                delete_nodes_after(process, sel_id)
                st.success("Passos posteriores removidos.")
                user_say(f"Deletei passos após {sel_idx} ({find_node(process, sel_id)['label']})")
                st.session_state.last_added_node = sel_id

    elif action == "Carregar processo (JSON)":
        uploaded = st.file_uploader("Envie um JSON de processo (formato do app)", type=["json"], key="upload_proc")
        if uploaded:
            try:
                content = json.load(uploaded)
                if "nodes" in content and "edges" in content:
                    st.session_state.process = content
                    st.success("Processo carregado.")
                    user_say("Carreguei um processo via upload.")
                else:
                    st.error("JSON inválido: precisa conter 'nodes' e 'edges'.")
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")

    else:
        st.write("_Escolha uma ação para avançar_")

    st.markdown("---")
    st.markdown("**Mensagens / Anotações rápidas**")
    note = st.text_input("Escreva algo (ex.: notas, comentários) e clique em 'Enviar' para registrar no chat.", key="note_input")
    if st.button("Enviar anotação"):
        if note.strip():
            user_say(note.strip())
            assistant_say("Anotação registrada. O que deseja fazer a seguir?")
            st.success("Anotação adicionada ao histórico.")
        else:
            st.warning("Escreva algo antes de enviar.")

# Footer / dicas
st.markdown("---")
st.markdown(
    """
    **Como usar este MVP**
    - Use a caixa à direita como um 'assistente' para adicionar tarefas, decisões e encerrar caminhos.
    - Se precisar editar um passo anterior, **deletar os passos posteriores** primeiro (regra do MVP). Use 'Deletar até um passo'.
    - Exporte o Mermaid com o botão 'Exportar Mermaid' e use mermaid.live para gerar imagens.
    """
)
