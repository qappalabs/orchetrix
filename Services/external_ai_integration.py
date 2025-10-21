"""
External AI Integration Examples for Orchestrix AI Assistant

This module shows how to integrate real AI models and services with the AI Assistant.
Currently the system uses rule-based analysis, but this shows how to add:
- OpenAI/ChatGPT integration
- Local AI models (Ollama, LM Studio)
- Hugging Face models
- Claude API integration
- Custom ML models

IMPORTANT: These are examples - you'll need API keys and proper setup.
"""

import logging
import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class AIResponse:
    """Structured response from AI service"""
    success: bool
    response: str
    confidence: float = 0.0
    reasoning: Optional[str] = None
    suggestions: List[str] = None
    error: Optional[str] = None


class OpenAIIntegration:
    """Integration with OpenAI ChatGPT API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        
    def analyze_cluster_logs(self, logs: List[str], context: Dict[str, Any]) -> AIResponse:
        """Analyze cluster logs using OpenAI"""
        if not self.api_key:
            return AIResponse(success=False, error="OpenAI API key not configured")
        
        try:
            prompt = self._create_log_analysis_prompt(logs, context)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a Kubernetes expert. Analyze logs and provide actionable insights."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.3
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
                
                return AIResponse(
                    success=True,
                    response=ai_response,
                    confidence=0.85,
                    reasoning="Analysis provided by GPT-4"
                )
            else:
                return AIResponse(
                    success=False,
                    error=f"OpenAI API error: {response.status_code}"
                )
                
        except Exception as e:
            logging.error(f"OpenAI integration error: {e}")
            return AIResponse(success=False, error=str(e))
    
    def answer_cluster_question(self, question: str, cluster_context: Dict[str, Any]) -> AIResponse:
        """Answer natural language questions about the cluster"""
        if not self.api_key:
            return AIResponse(success=False, error="OpenAI API key not configured")
        
        try:
            prompt = f"""
Kubernetes Cluster Context:
- Nodes: {cluster_context.get('nodes', 'Unknown')}
- Pods: {cluster_context.get('pods', 'Unknown')}
- Services: {cluster_context.get('services', 'Unknown')}
- CPU Usage: {cluster_context.get('cpu_usage', 'Unknown')}%
- Memory Usage: {cluster_context.get('memory_usage', 'Unknown')}%

Question: {question}

Please provide a detailed answer with specific recommendations for this Kubernetes cluster.
"""
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful Kubernetes expert providing practical advice."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.4
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
                
                return AIResponse(
                    success=True,
                    response=ai_response,
                    confidence=0.80
                )
            else:
                return AIResponse(
                    success=False,
                    error=f"OpenAI API error: {response.status_code}"
                )
                
        except Exception as e:
            logging.error(f"OpenAI question answering error: {e}")
            return AIResponse(success=False, error=str(e))
    
    def _create_log_analysis_prompt(self, logs: List[str], context: Dict[str, Any]) -> str:
        """Create a structured prompt for log analysis"""
        log_sample = logs[:20]  # Analyze first 20 logs
        
        return f"""
Analyze these Kubernetes cluster logs:

Cluster Context:
- Cluster Name: {context.get('cluster_name', 'Unknown')}
- Nodes: {context.get('node_count', 'Unknown')}
- Namespace: {context.get('namespace', 'All')}

Log Sample ({len(log_sample)} of {len(logs)} entries):
{chr(10).join(log_sample)}

Please provide:
1. Key issues identified
2. Severity assessment (1-5)
3. Root cause analysis
4. Specific remediation steps
5. Prevention recommendations

Format your response in clear sections with actionable advice.
"""


class OllamaIntegration:
    """Integration with local Ollama models"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "llama2"  # Default model
    
    def analyze_with_local_model(self, prompt: str) -> AIResponse:
        """Analyze using local Ollama model"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get("response", "")
                
                return AIResponse(
                    success=True,
                    response=ai_response,
                    confidence=0.70,
                    reasoning=f"Analysis from local {self.model} model"
                )
            else:
                return AIResponse(
                    success=False,
                    error=f"Ollama error: {response.status_code}"
                )
                
        except Exception as e:
            logging.error(f"Ollama integration error: {e}")
            return AIResponse(success=False, error=str(e))


class ClaudeIntegration:
    """Integration with Anthropic Claude API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"
    
    def analyze_cluster_security(self, security_data: Dict[str, Any]) -> AIResponse:
        """Analyze cluster security using Claude"""
        if not self.api_key:
            return AIResponse(success=False, error="Claude API key not configured")
        
        try:
            prompt = f"""
Analyze this Kubernetes cluster security configuration:

Security Data:
{json.dumps(security_data, indent=2)}

Please provide:
1. Security score (1-10)
2. Critical vulnerabilities
3. Best practice violations
4. Specific remediation steps
5. Long-term security improvements

Focus on actionable, prioritized recommendations.
"""
            
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = requests.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["content"][0]["text"]
                
                return AIResponse(
                    success=True,
                    response=ai_response,
                    confidence=0.90,
                    reasoning="Security analysis by Claude-3"
                )
            else:
                return AIResponse(
                    success=False,
                    error=f"Claude API error: {response.status_code}"
                )
                
        except Exception as e:
            logging.error(f"Claude integration error: {e}")
            return AIResponse(success=False, error=str(e))


class HuggingFaceIntegration:
    """Integration with Hugging Face models"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api-inference.huggingface.co/models"
    
    def analyze_text_with_model(self, text: str, model_name: str = "microsoft/DialoGPT-large") -> AIResponse:
        """Analyze text using Hugging Face model"""
        if not self.api_key:
            return AIResponse(success=False, error="Hugging Face API key not configured")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "inputs": text,
                "parameters": {
                    "max_length": 500,
                    "temperature": 0.7
                }
            }
            
            response = requests.post(
                f"{self.base_url}/{model_name}",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result[0].get("generated_text", "")
                
                return AIResponse(
                    success=True,
                    response=ai_response,
                    confidence=0.75,
                    reasoning=f"Analysis from {model_name}"
                )
            else:
                return AIResponse(
                    success=False,
                    error=f"Hugging Face error: {response.status_code}"
                )
                
        except Exception as e:
            logging.error(f"Hugging Face integration error: {e}")
            return AIResponse(success=False, error=str(e))


class AIOrchestrator:
    """Orchestrates multiple AI services for best results"""
    
    def __init__(self):
        # Initialize all AI services
        self.openai = None
        self.claude = None
        self.ollama = None
        self.huggingface = None
        
        # Try to load API keys from environment or config
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize available AI services"""
        import os
        
        # OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.openai = OpenAIIntegration(openai_key)
            logging.info("OpenAI integration initialized")
        
        # Claude
        claude_key = os.getenv("ANTHROPIC_API_KEY")
        if claude_key:
            self.claude = ClaudeIntegration(claude_key)
            logging.info("Claude integration initialized")
        
        # Ollama (check if local server is running)
        try:
            requests.get("http://localhost:11434", timeout=2)
            self.ollama = OllamaIntegration()
            logging.info("Ollama integration initialized")
        except:
            pass
        
        # Hugging Face
        hf_key = os.getenv("HUGGINGFACE_API_KEY")
        if hf_key:
            self.huggingface = HuggingFaceIntegration(hf_key)
            logging.info("Hugging Face integration initialized")
    
    def get_best_ai_response(self, query: str, context: Dict[str, Any], preferred_service: str = None) -> AIResponse:
        """Get the best AI response using available services"""
        
        # If a preferred service is specified and available, use it
        if preferred_service:
            service = getattr(self, preferred_service.lower(), None)
            if service:
                if preferred_service.lower() == "openai" and self.openai:
                    return self.openai.answer_cluster_question(query, context)
                elif preferred_service.lower() == "claude" and self.claude:
                    return self.claude.analyze_cluster_security(context)
                elif preferred_service.lower() == "ollama" and self.ollama:
                    prompt = f"Kubernetes question: {query}\nContext: {json.dumps(context)}"
                    return self.ollama.analyze_with_local_model(prompt)
        
        # Otherwise, use the best available service based on query type
        query_lower = query.lower()
        
        # Security-related queries -> Claude (best for security analysis)
        if any(word in query_lower for word in ['security', 'rbac', 'vulnerability', 'secure']):
            if self.claude:
                return self.claude.analyze_cluster_security(context)
        
        # Complex analysis queries -> OpenAI (best for complex reasoning)
        if any(word in query_lower for word in ['analyze', 'complex', 'troubleshoot', 'debug']):
            if self.openai:
                return self.openai.answer_cluster_question(query, context)
        
        # Simple queries -> Local model (faster, private)
        if self.ollama:
            prompt = f"Kubernetes question: {query}\nContext: {json.dumps(context, indent=2)}"
            return self.ollama.analyze_with_local_model(prompt)
        
        # Fallback to any available service
        for service in [self.openai, self.claude, self.huggingface]:
            if service:
                if hasattr(service, 'answer_cluster_question'):
                    return service.answer_cluster_question(query, context)
        
        return AIResponse(
            success=False,
            error="No AI services available. Configure API keys or install local models."
        )


# Global AI orchestrator instance
_ai_orchestrator = None

def get_ai_orchestrator() -> AIOrchestrator:
    """Get global AI orchestrator instance"""
    global _ai_orchestrator
    if _ai_orchestrator is None:
        _ai_orchestrator = AIOrchestrator()
    return _ai_orchestrator


# Integration example for the existing AI Assistant
def enhance_ai_assistant_with_real_ai():
    """
    Example of how to integrate real AI into the existing AIAssistantPage
    
    Add this to your ChatWidget.process_query method:
    """
    example_code = '''
def process_query(self, query: str) -> str:
    """Enhanced process query with real AI integration"""
    # Try real AI first
    try:
        ai_orchestrator = get_ai_orchestrator()
        
        # Get current cluster context
        context = {
            'cluster_name': 'my-cluster',
            'nodes': 5,
            'pods': 127,
            'cpu_usage': 45.2,
            'memory_usage': 68.5
        }
        
        response = ai_orchestrator.get_best_ai_response(query, context)
        
        if response.success:
            return f"🤖 **AI Analysis:**\\n\\n{response.response}"
        else:
            logging.warning(f"AI service failed: {response.error}")
            # Fall back to rule-based responses
            
    except Exception as e:
        logging.error(f"AI integration error: {e}")
        # Fall back to rule-based responses
    
    # Existing rule-based logic as fallback
    query_lower = query.lower()
    
    if any(word in query_lower for word in ['memory', 'ram', 'mem']):
        return self._handle_memory_query(query)
    # ... rest of existing logic
    '''
    
    return example_code


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    print("🤖 External AI Integration Examples")
    print("=" * 50)
    
    orchestrator = get_ai_orchestrator()
    
    # Test query
    test_query = "What should I do about high memory usage in my cluster?"
    test_context = {
        'cluster_name': 'test-cluster',
        'nodes': 3,
        'pods': 50,
        'cpu_usage': 45.0,
        'memory_usage': 85.0
    }
    
    print(f"Query: {test_query}")
    print(f"Context: {test_context}")
    
    response = orchestrator.get_best_ai_response(test_query, test_context)
    
    if response.success:
        print(f"✅ AI Response: {response.response}")
    else:
        print(f"❌ Error: {response.error}")
    
    print("\n💡 To enable real AI:")
    print("1. Set environment variables:")
    print("   export OPENAI_API_KEY='your-key'")
    print("   export ANTHROPIC_API_KEY='your-key'")
    print("2. Install local models (Ollama)")
    print("3. Integrate the AIOrchestrator into your ChatWidget")