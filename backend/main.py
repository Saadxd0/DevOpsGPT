import os
import subprocess
import json
import re
import shlex
import shutil
import logging
from typing import List, Dict, Any, Set, Optional, Tuple, TypedDict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, END

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DevOpsGPT")

# Load environment variables
load_dotenv()

app = FastAPI(title="DevOpsGPT Unified Automation Engine", version="10.1.0")

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set.")

client = genai.Client(api_key=api_key)

# ============================================================================
# SECURITY POLICY CONFIGURATION
# ============================================================================

# Executables that are explicitly allowed to run
ALLOWED_EXECUTABLES: Set[str] = {
    # Container & Orchestration
    "docker", "docker-compose", "kubectl", "helm", "containerd", "ctr",
    # Infrastructure as Code
    "terraform", "terragrunt", "ansible", "ansible-playbook",
    # Version Control
    "git", "gh",
    # System & Service Management
    "systemctl", "journalctl", "service",
    # Build & Package Management
    "make", "npm", "node", "python", "python3", "pip", "pip3",
    # File & Directory Operations
    "ls", "pwd", "cat", "echo", "mkdir", "cp", "mv", "rm", "touch",
    "chmod", "chown", "find", "grep", "sed", "awk", "stat", "du", "df",
    # Network & Transfer
    "curl", "wget", "ssh", "scp", "rsync", "ping", "netstat", "ss",
    # Process Management
    "ps", "top", "htop", "kill", "killall",
    # Text Processing
    "head", "tail", "sort", "uniq", "wc", "cut", "tr", "tee",
    # Compression
    "tar", "gzip", "gunzip", "zip", "unzip",
    # Shell Builtins (allowed for scripting constructs)
    "true", "false", "test", "[", "echo", "printf", "cd",
}

# Executables that are explicitly blocked (even if in ALLOWED_EXECUTABLES)
BLOCKED_EXECUTABLES: Set[str] = {
    "shutdown", "reboot", "halt", "poweroff", "init",
    "mkfs", "mkfs.ext4", "mkfs.xfs", "mkfs.btrfs",
    "dd", "fdisk", "parted", "wipefs",
    "sudo", "su", "doas",
    "passwd", "chpasswd",
}

# Dangerous patterns that should be blocked regardless of executable
BLOCKED_PATTERNS: List[str] = [
    r"rm\s+-rf\s+/",                    # rm -rf /
    r"rm\s+-rf\s+~",                    # rm -rf ~
    r"rm\s+-rf\s+\$HOME",              # rm -rf $HOME
    r"chmod\s+-R\s+777\s+/",           # chmod -R 777 /
    r"chmod\s+-R\s+777\s+/",           # chmod -R 777 /
    r"chown\s+-R\s+/",                 # chown -R /
    r"chown\s+-R\s+~",                 # chown -R ~
    r":\(\)\s*\{\s*:\|\:&\s*\}\s*;",   # Fork bomb
    r"curl.*\|\s*(ba)?sh",             # curl | sh
    r"wget.*\|\s*(ba)?sh",             # wget | sh
    r">\s*/dev/sda",                   # Overwrite disk
    r">\s*/dev/null\s+2>&1\s*&&\s*reboot",  # Obscured dangerous
    r"mkfs\.",                         # Any mkfs variant
    r"dd\s+if=",                       # dd usage
]

# Maximum execution time in seconds
EXECUTION_TIMEOUT: int = int(os.getenv("EXECUTION_TIMEOUT", "30"))

# ============================================================================
# COMMAND PARSING & VALIDATION HELPERS
# ============================================================================

def extract_executables(command: str) -> List[Tuple[str, str]]:
    """
    Extract executable names from a command string.
    Returns list of (executable, raw_command_segment) tuples.
    Handles command substitution, pipes, and shell operators.
    """
    executables = []
    
    # Split by common command separators first
    # This handles &&, ||, ;, |, newlines
    segments = re.split(r'(?:&&|\|\||[;|]|\n)', command)
    
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
            
        # Remove command substitution $(...) for analysis
        # We replace with placeholder to preserve surrounding structure
        cleaned = re.sub(r'\$\([^)]*\)', '__CMDSUB__', segment)
        cleaned = re.sub(r'`[^`]*`', '__CMDSUB__', cleaned)
        
        # Try to parse with shlex
        try:
            tokens = shlex.split(cleaned)
            if tokens:
                # First token is usually the executable
                exe = tokens[0]
                # Handle paths (e.g., /usr/bin/docker -> docker)
                if '/' in exe:
                    exe = os.path.basename(exe)
                executables.append((exe, segment))
        except ValueError:
            # Fallback: try to extract first word
            words = cleaned.split()
            if words:
                exe = words[0]
                if '/' in exe:
                    exe = os.path.basename(exe)
                executables.append((exe, segment))
    
    return executables

def check_dangerous_patterns(command: str) -> Optional[str]:
    """
    Check if command contains any dangerous patterns.
    Returns the matched pattern description if dangerous, None otherwise.
    """
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return f"Command contains forbidden pattern: {pattern}"
    return None

def validate_command_security(command: str) -> Tuple[bool, str]:
    """
    Validate a command against security policies.
    Returns (is_allowed, reason).
    """
    if not command or not command.strip():
        return False, "Empty command"
    
    command = command.strip()
    logger.info(f"Validating command: {command}")
    
    # Check for dangerous patterns first (highest priority)
    pattern_block = check_dangerous_patterns(command)
    if pattern_block:
        logger.warning(f"Blocked by pattern: {pattern_block}")
        return False, pattern_block
    
    # Extract and validate executables
    executables = extract_executables(command)
    
    if not executables:
        return False, "Unable to parse executable from command"
    
    for exe_name, segment in executables:
        # Check if executable is explicitly blocked
        if exe_name in BLOCKED_EXECUTABLES:
            logger.warning(f"Blocked executable: {exe_name}")
            return False, f"Blocked because executable '{exe_name}' is in the deny list for safety reasons"
        
        # Check if executable is allowed
        if exe_name not in ALLOWED_EXECUTABLES:
            # Check if it exists as a system binary (additional safety)
            if shutil.which(exe_name):
                logger.warning(f"Executable exists but not in allowlist: {exe_name}")
                return False, f"Blocked because executable '{exe_name}' is not in the allowlist. Add it to ALLOWED_EXECUTABLES if safe"
            else:
                logger.warning(f"Executable not found: {exe_name}")
                return False, f"Blocked because executable '{exe_name}' is not recognized or not in the allowlist"
    
    logger.info(f"Command validation passed: {command}")
    return True, "Command validated successfully"

def execute_command_safely(command: str, timeout: int = EXECUTION_TIMEOUT) -> Dict[str, Any]:
    """
    Execute a validated command safely.
    Returns dict with stdout, stderr, return_code, and success status.
    """
    try:
        logger.info(f"Executing command: {command}")
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            executable='/bin/bash',  # Explicitly use bash for consistency
            env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'}  # Prevent interactive prompts
        )
        
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        
        logger.info(f"Command completed with exit code: {result.returncode}")
        
        if result.returncode == 0:
            logger.info(f"Command stdout: {stdout[:200]}...")
        else:
            logger.warning(f"Command stderr: {stderr[:200]}...")
        
        return {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "command": command
        }
    
    except subprocess.TimeoutExpired:
        logger.error(f"Command timeout after {timeout}s: {command}")
        return {
            "success": False,
            "return_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "command": command
        }
    except Exception as e:
        logger.error(f"Execution error: {str(e)}")
        return {
            "success": False,
            "return_code": -1,
            "stdout": "",
            "stderr": f"Execution error: {str(e)}",
            "command": command
        }

# --- Universal Graph State ---
class AgentState(TypedDict):
    message: str
    history: List[Dict[str, str]]
    next_step: str
    command_type: str        # "READ" or "MUTATION"
    target_domain: str       # "INFRA", "DOCKER", "K8S", "GIT", "TERRAFORM", "DIRECT"
    raw_logs: str
    final_response: str
    requires_approval: bool
    proposed_command: str
    approved_command: str

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    history: List[Message]
    message: str

# --- Agent Nodes ---

def supervisor_node(state: AgentState) -> Dict[str, Any]:
    print("🤖 [Supervisor]: Analyzing intent and routing query...")
    
    # 1. HITL Check: Did the user just reply to an approval prompt?
    if len(state['history']) > 0:
        last_ai_msg = state['history'][-1]
        if last_ai_msg.get('role') == 'model' and "⚠️ **Approval Required**" in last_ai_msg.get('content', ''):
            user_msg = state['message'].strip().lower()
            if user_msg in ['yes', 'y', 'approve', 'do it', 'execute', 'go ahead']:
                match = re.search(r'`(.*?)`', last_ai_msg['content'])
                if match:
                    cmd = match.group(1)
                    print(f"✅ [Supervisor]: User approved execution of: {cmd}")
                    return {"next_step": "EXECUTION_AGENT", "approved_command": cmd}
            else:
                return {"next_step": "DIRECT_ANSWER", "final_response": "Execution cancelled. Let me know if you need anything else!"}

    # 2. Hardened Intent Router
    prompt = (
        "Analyze the user's infrastructure query. You must decide if it is a safe READ command or a MUTATION.\n"
        "CRITICAL RULE: If the user explicitly asks to 'delete', 'remove', 'rmi', 'stop', 'kill', 'create', 'make', or 'build' "
        "any container, image, pod, file, folder, or infrastructure resource, you MUST classify it as a MUTATION and output the exact system command to complete it.\n"
        "Output your classification as JSON matching this schema:\n"
        "{\n"
        "  \"domain\": \"INFRA\" | \"DOCKER\" | \"K8S\" | \"GIT\" | \"TERRAFORM\" | \"DIRECT\",\n"
        "  \"intent_type\": \"READ\" | \"MUTATION\",\n"
        "  \"drafted_command\": \"raw bash command to execute user request\"\n"
        "}\n\n"
        f"Query: {state['message']}"
    )
    
    try:
        decision_raw = client.models.generate_content(
            model='gemini-2.5-flash', contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        ).text.strip()
        decision = json.loads(decision_raw)
    except Exception as e:
        print(f"❌ [Supervisor Error]: Fallback routing due to: {e}")
        decision = {"domain": "DIRECT", "intent_type": "READ", "drafted_command": ""}

    domain = decision.get("domain", "DIRECT")
    intent = decision.get("intent_type", "READ")
    command = decision.get("drafted_command", "")

    # Trigger approval block immediately if a mutation was planned
    if intent == "MUTATION" and command:
        print(f"⚠️ [Supervisor]: Mutation detected for command: {command}. Routing to Approval Gate.")
        return {
            "next_step": "APPROVAL_GATE",
            "proposed_command": command,
            "command_type": "MUTATION",
            "target_domain": domain
        }

    mapping = {
        "INFRA": "INFRA_AGENT",
        "DOCKER": "DOCKER_AGENT",
        "K8S": "K8S_AGENT",
        "GIT": "GIT_AGENT",
        "TERRAFORM": "TERRAFORM_AGENT"
    }
    
    return {
        "next_step": mapping.get(domain, "DIRECT_ANSWER"),
        "command_type": "READ",
        "target_domain": domain,
        "proposed_command": command
    }

def infra_agent_node(state: AgentState) -> Dict[str, Any]:
    print("🖥️ [Infra Agent]: Fetching resource telemetry...")
    cmd = state.get("proposed_command") or "free -h"
    raw_output = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
    return {"raw_logs": f"System Metrics:\n{raw_output}", "next_step": "SYNTHESIS"}

def docker_agent_node(state: AgentState) -> Dict[str, Any]:
    print("🐳 [Docker Agent]: Querying container runtimes...")
    cmd = state.get("proposed_command") or "docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Status}}'"
    raw_output = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
    return {"raw_logs": f"Docker Environment Diagnostics:\n{raw_output}", "next_step": "SYNTHESIS"}

def k8s_agent_node(state: AgentState) -> Dict[str, Any]:
    print("☸️ [K8s Agent]: Inspecting cluster orchestration state...")
    cmd = state.get("proposed_command") or "kubectl get pods,services,deployments -o wide"
    raw_output = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
    return {"raw_logs": f"Kubernetes Cluster State:\n{raw_output}", "next_step": "SYNTHESIS"}

def git_agent_node(state: AgentState) -> Dict[str, Any]:
    print("🐙 [Git Agent]: Analyzing revision histories...")
    cmd = state.get("proposed_command") or "git log -n 3 --oneline"
    raw_output = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout or "No active local git configuration found."
    return {"raw_logs": f"Git Revision Timeline:\n{raw_output}", "next_step": "SYNTHESIS"}

def terraform_agent_node(state: AgentState) -> Dict[str, Any]:
    print("🧱 [Terraform Agent]: Validating infrastructure blueprints...")
    cmd = state.get("proposed_command") or "terraform show"
    raw_output = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout or "No local terraform plan state found."
    return {"raw_logs": f"Terraform Workspace Plan State:\n{raw_output}", "next_step": "SYNTHESIS"}

def execution_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Production-grade execution agent with proper command validation,
    shell operator support, and comprehensive security checks.
    """
    cmd = state.get("approved_command", "")
    if not cmd:
        return {"final_response": "❌ No command provided for execution"}
    
    logger.info(f"🚀 [Execution Agent]: Validating and executing command: {cmd}")
    print(f"🚀 [Execution Agent]: Processing command: {cmd}")
    
    # Step 1: Validate security
    is_valid, validation_message = validate_command_security(cmd)
    if not is_valid:
        logger.warning(f"Security validation failed: {validation_message}")
        return {"final_response": f"❌ **Security Block:** {validation_message}"}
    
    # Step 2: Execute command safely
    result = execute_command_safely(cmd, timeout=EXECUTION_TIMEOUT)
    
    # Step 3: Format response
    if result["success"]:
        stdout = result["stdout"].strip() if result["stdout"] else "Success (No output)"
        stderr = result["stderr"].strip() if result["stderr"] else ""
        
        response = f"✅ **Command Executed Successfully** (exit code: {result['return_code']})\n"
        response += f"```bash\n{stdout}\n```"
        if stderr:
            response += f"\n⚠️ **Stderr output:**\n```bash\n{stderr}\n```"
    else:
        stdout = result["stdout"].strip() if result["stdout"] else ""
        stderr = result["stderr"].strip() if result["stderr"] else "No error output"
        
        response = f"❌ **Command Failed** (exit code: {result['return_code']})\n"
        if stdout:
            response += f"**Stdout:**\n```bash\n{stdout}\n```\n"
        response += f"**Stderr:**\n```bash\n{stderr}\n```"
    
    logger.info(f"Execution complete for command: {cmd}")
    return {"final_response": response}

def approval_gate_node(state: AgentState) -> Dict[str, Any]:
    print("🛑 [Approval Gate]: Holding execution pipeline...")
    cmd = state.get('proposed_command', 'unknown command')
    response = f"⚠️ **Approval Required**\n\nI have drafted the following command to fulfill your request:\n\n`{cmd}`\n\nDo you want me to execute this? (Reply **Yes** or **No**)"
    return {"final_response": response}

def synthesis_node(state: AgentState) -> Dict[str, Any]:
    print("✍️ [Synthesis]: Compiling pinpoint response from operational logs...")
    instruction = (
        "You are DevOpsGPT, a precise engineering assistant. "
        "Answer the user's query directly and concisely using ONLY the provided logs. "
        "Do NOT write unsolicited advice, essays, background theory, or long recommendation lists "
        "unless explicitly requested. Keep it clean, professional, and brief."
    )
    payload = f"User Query: {state['message']}\n\n[Collected System State Logs]:\n{state.get('raw_logs', 'No logs available.')}"
    
    response = client.models.generate_content(
        model='gemini-2.5-flash', contents=payload,
        config=types.GenerateContentConfig(system_instruction=instruction)
    )
    return {"final_response": response.text}

def direct_answer_node(state: AgentState) -> Dict[str, Any]:
    print("💬 [Direct Answer]: Generating conversational feedback...")
    custom_msg = state.get("final_response")
    if custom_msg:
        return {"final_response": custom_msg}
        
    response = client.models.generate_content(model='gemini-2.5-flash', contents=state['message'])
    return {"final_response": response.text}

# --- State Graph Compilation ---
workflow = StateGraph(AgentState)

workflow.add_node("Supervisor", supervisor_node)
workflow.add_node("InfraAgent", infra_agent_node)
workflow.add_node("DockerAgent", docker_agent_node)
workflow.add_node("K8sAgent", k8s_agent_node)
workflow.add_node("GitAgent", git_agent_node)
workflow.add_node("TerraformAgent", terraform_agent_node)
workflow.add_node("ExecutionAgent", execution_agent_node)
workflow.add_node("ApprovalGate", approval_gate_node)
workflow.add_node("Synthesis", synthesis_node)
workflow.add_node("DirectAnswer", direct_answer_node)

workflow.set_entry_point("Supervisor")

def supervisor_router(state):
    mapping = {
        "INFRA_AGENT": "to_infra",
        "DOCKER_AGENT": "to_docker",
        "K8S_AGENT": "to_k8s",
        "GIT_AGENT": "to_git",
        "TERRAFORM_AGENT": "to_terraform",
        "EXECUTION_AGENT": "to_execute",
        "APPROVAL_GATE": "to_approval"
    }
    return mapping.get(state["next_step"], "to_direct")

workflow.add_conditional_edges(
    "Supervisor", supervisor_router,
    {
        "to_infra": "InfraAgent",
        "to_docker": "DockerAgent",
        "to_k8s": "K8sAgent",
        "to_terraform": "TerraformAgent",
        "to_git": "GitAgent",
        "to_execute": "ExecutionAgent",
        "to_approval": "ApprovalGate",
        "to_direct": "DirectAnswer"
    }
)

workflow.add_edge("InfraAgent", "Synthesis")
workflow.add_edge("DockerAgent", "Synthesis")
workflow.add_edge("K8sAgent", "Synthesis")
workflow.add_edge("GitAgent", "Synthesis")
workflow.add_edge("TerraformAgent", "Synthesis")

workflow.add_edge("Synthesis", END)
workflow.add_edge("ApprovalGate", END)
workflow.add_edge("ExecutionAgent", END)
workflow.add_edge("DirectAnswer", END)

graph_app = workflow.compile()

@app.post("/api/v1/chat")
async def langgraph_chat_endpoint(payload: ChatRequest):
    try:
        initial_state = {
            "message": payload.message,
            "history": [m.dict() for m in payload.history],
            "next_step": "",
            "command_type": "",
            "target_domain": "",
            "raw_logs": "",
            "final_response": "",
            "requires_approval": False,
            "proposed_command": "",
            "approved_command": ""
        }
        final_state = graph_app.invoke(initial_state)
        return {"response": final_state["final_response"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))