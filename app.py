# app.py - Streamlit Chat Interface with Complete Exception Handling

import streamlit as st
import time
import logging
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Page Configuration (MUST be first) ────────────────────
st.set_page_config(
    page_title='SRE Ops Copilot',
    page_icon='🔍',
    layout='wide',
    initial_sidebar_state='expanded'
)

# ── Import modules with error handling ────────────────────
try:
    from rag import ask, ask_stream, get_authorized_customers, collection
    from logger import log_query
    from auth import check_login, get_user_customers as auth_get_customers
except ImportError as e:
    st.error(f"❌ Critical error: Missing module - {e}")
    st.stop()
except Exception as e:
    st.error(f"❌ Initialization error: {e}")
    st.stop()

# ── Custom CSS ─────────────────────────────────────────────
st.markdown('''
<style>
    .source-chip {
        background: #E8F0FE;
        border: 1px solid #C5D0EF;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 12px;
        margin-right: 6px;
        color: #1B4F8A;
        display: inline-block;
    }
</style>
''', unsafe_allow_html=True)

# ── Session State Initialization ───────────────────────────
try:
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_info = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
except Exception as e:
    logger.error(f"Session state initialization error: {e}")
    st.error("Error initializing session. Please refresh the page.")
    st.stop()

# ── Login Gate with Exception Handling ─────────────────────
if not st.session_state.authenticated:
    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        st.title('🔍 SRE Ops Copilot')
        st.subheader('Sign in to continue')
        st.divider()

        with st.form('login_form'):
            username = st.text_input('Username')
            password = st.text_input('Password', type='password')
            submit = st.form_submit_button('Sign in', use_container_width=True)

        if submit:
            try:
                if not username or not password:
                    st.error('Please enter both username and password.')
                else:
                    user_info = check_login(username, password)
                    if user_info:
                        st.session_state.authenticated = True
                        st.session_state.user_info = user_info
                        st.rerun()
                    else:
                        st.error('Incorrect username or password.')
            except FileNotFoundError:
                st.error('❌ User database not found. Contact administrator.')
            except Exception as e:
                logger.error(f"Login error: {e}")
                st.error(f'Login system error. Please try again.')
    
    st.stop()

# ── Authenticated Section ──────────────────────────────────
try:
    user_info = st.session_state.user_info
    current_user = user_info['username']
except (KeyError, TypeError) as e:
    logger.error(f"User info error: {e}")
    st.error("Session corrupted. Please log in again.")
    st.session_state.authenticated = False
    st.rerun()

# ── Sidebar with Exception Handling ────────────────────────
try:
    st.sidebar.metric('Total knowledge chunks', collection.count())
except Exception as e:
    logger.warning(f"Error getting collection count: {e}")
    st.sidebar.metric('Total knowledge chunks', 'N/A')

with st.sidebar:
    st.title('SRE Ops Copilot')
    st.caption('AI-powered deployment knowledge base')
    st.divider()
 
    # Show logged-in user
    try:
        st.success(f"✓ {user_info['display_name']}")
        if st.button('Sign out'):
            st.session_state.authenticated = False
            st.session_state.user_info = None
            st.session_state.messages = []
            st.rerun()
    except Exception as e:
        logger.error(f"Sidebar user display error: {e}")
        st.error("Display error")
    
    st.divider()
    
    # Get customer scope
    try:
        authorized_customers = user_info['customers']
    except (KeyError, TypeError):
        logger.warning("Customers key missing from user_info")
        authorized_customers = ['General']
 
    # Customer scope selector
    try:
        customer_scope = st.multiselect(
            'Search within customers',
            options=authorized_customers,
            default=authorized_customers,
            help='Only documents for selected customers will be searched'
        )
    except Exception as e:
        logger.error(f"Customer selector error: {e}")
        customer_scope = authorized_customers
 
    st.divider()
 
    # Suggested questions
    st.subheader('Try asking:')
    example_questions = [
        'What version is CustomerX running?',
        'What AKS node pool does CustomerX use?',
        'Who are the escalation contacts for CustomerX?',
        'Are there any known issues for CustomerX?',
    ]
    
    for q in example_questions:
        try:
            if st.button(q, use_container_width=True, key=q):
                st.session_state['prefilled_question'] = q
        except Exception as e:
            logger.warning(f"Button error for question: {e}")
            continue
 
    st.divider()
 
    # Clear chat button
    try:
        if st.button('Clear conversation', use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    except Exception as e:
        logger.error(f"Clear button error: {e}")

# ── Main Chat Area ─────────────────────────────────────────
st.header('SRE Knowledge Base')
try:
    st.caption(f'Searching as: {current_user} | Scope: {", ".join(customer_scope) if customer_scope else "None"}')
except Exception:
    st.caption(f'Searching as: {current_user}')

st.divider()
st.caption('SRE Ops Copilot · Powered by Gemini · Answers are grounded in retrieved documentation only.')

# Check customer scope
if not customer_scope:
    st.warning('⚠️ No customers selected. Select at least one customer in the sidebar.')
    st.stop()

# Display welcome message
try:
    if not st.session_state.messages:
        st.info('Ask me anything about your customer deployments. I will search the knowledge base and cite my sources.')
except Exception as e:
    logger.error(f"Welcome message error: {e}")

# ── Render Chat History with Exception Handling ────────────
try:
    for msg in st.session_state.messages:
        try:
            with st.chat_message(msg['role']):
                st.write(msg['content'])
         
                if msg['role'] == 'assistant' and msg.get('sources'):
                    sources = msg['sources']
                    try:
                        chips_html = ' '.join([
                            f'<span class="source-chip">{s["source"].split("/")[-1]}</span>'
                            for s in sources[:3]
                        ])
                        st.markdown(f'**Sources:** {chips_html}', unsafe_allow_html=True)
                    except Exception as chip_error:
                        logger.warning(f"Source chip error: {chip_error}")
                    
                    try:
                        with st.expander(f'View {len(sources)} source(s)'):
                            for src in sources:
                                col1, col2, col3 = st.columns([3, 1, 1])
                                col1.text(src.get('source', 'Unknown'))
                                col2.text(src.get('customer', 'General'))
                                col3.text(f"{src.get('similarity', 0):.0%} match")
                    except Exception as expander_error:
                        logger.warning(f"Source expander error: {expander_error}")
        except Exception as msg_error:
            logger.error(f"Message render error: {msg_error}")
            continue
except Exception as e:
    logger.error(f"Chat history render error: {e}")

# ── Chat Input with Exception Handling ─────────────────────
try:
    prefilled = st.session_state.pop('prefilled_question', None)
except Exception:
    prefilled = None

try:
    user_input = st.chat_input('Ask about any customer deployment...')
except Exception as e:
    logger.error(f"Chat input error: {e}")
    user_input = None

prompt = prefilled or user_input

# ── Process Question with Complete Exception Handling ──────
if prompt:
    if not customer_scope:
        st.error('Select at least one customer from the sidebar.')
        st.stop()

    # Display user question
    try:
        with st.chat_message('user'):
            st.write(prompt)
        
        st.session_state.messages.append({
            'role': 'user',
            'content': prompt
        })
    except Exception as e:
        logger.error(f"Error displaying user message: {e}")
        st.error("Failed to display your question. Please try again.")
        st.stop()

    # Generate answer with streaming
    with st.chat_message('assistant'):
        sources_holder = []
        full_answer = ""
        success = True
        error_msg = None
        
        def text_only_stream():
            '''Wrapper to separate text from sources with error handling'''
            try:
                for piece in ask_stream(prompt, customer_scope):
                    if isinstance(piece, list):
                        sources_holder.extend(piece)
                    else:
                        yield piece
            except Exception as stream_error:
                logger.error(f"Streaming error: {stream_error}")
                yield f"\n\n❌ Error during streaming: {str(stream_error)[:100]}"
        
        start_time = time.time()
        
        try:
            full_answer = st.write_stream(text_only_stream())
            success = True
        except Exception as e:
            logger.error(f"Stream display error: {e}")
            full_answer = f'Error generating answer: {e}'
            st.error(full_answer)
            success = False
            error_msg = str(e)
        
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        sources = sources_holder
        
        # Display sources
        try:
            if sources:
                chips_html = ' '.join([
                    f'<span class="source-chip">{s.get("source", "Unknown").split("/")[-1]}</span>'
                    for s in sources[:3]
                ])
                st.markdown(f'**Sources:** {chips_html}', unsafe_allow_html=True)

                with st.expander(f'View {len(sources)} source(s)'):
                    for src in sources:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        col1.text(src.get('source', 'Unknown'))
                        col2.text(src.get('customer', 'General'))
                        col3.text(f"{src.get('similarity', 0):.0%} match")
        except Exception as source_error:
            logger.warning(f"Source display error: {source_error}")
        
        # Log query
        try:
            log_query(
                username=current_user,
                question=prompt,
                customer_scope=customer_scope,
                answer=full_answer,
                sources=sources,
                latency_ms=latency_ms,
                success=success,
                error=error_msg
            )
        except Exception as log_error:
            logger.error(f"Logging error: {log_error}")
    
    # Save to history
    try:
        st.session_state.messages.append({
            'role': 'assistant',
            'content': full_answer,
            'sources': sources
        })
    except Exception as history_error:
        logger.error(f"Error saving to history: {history_error}")