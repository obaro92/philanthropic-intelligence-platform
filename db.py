"""
Database integration layer for Access Digital Health Philanthropic Intelligence Platform.
Uses Supabase (PostgreSQL) for persistent storage across sessions.
Falls back gracefully to session-only storage if Supabase is not configured.
"""

import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


class Database:
    """Handles all persistent storage. Falls back to in-memory if Supabase unavailable."""
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        self.client: Optional[Client] = None
        self.connected = False
        
        if SUPABASE_AVAILABLE and supabase_url and supabase_key:
            try:
                self.client = create_client(supabase_url, supabase_key)
                self.connected = True
            except Exception as e:
                print(f"Supabase connection failed: {e}")
                self.connected = False
        
        # In-memory fallback for when Supabase is not available
        self._memory = {
            "users": {},
            "portfolio_grants": {},
            "evaluations": [],
            "conversations": {},
            "report_analyses": {},
            "data_cache": {},
            "board_reports": [],
        }
    
    # ══════════════════════════════════════════
    # USER MANAGEMENT
    # ══════════════════════════════════════════
    
    def get_or_create_user(self, email: str, display_name: str = None) -> dict:
        """Get existing user or create a new one. Returns user dict."""
        if self.connected:
            try:
                result = self.client.table("users").select("*").eq("email", email).execute()
                if result.data:
                    return result.data[0]
                # Create new user
                new_user = {"email": email, "display_name": display_name or email.split("@")[0]}
                result = self.client.table("users").insert(new_user).execute()
                return result.data[0] if result.data else new_user
            except Exception as e:
                print(f"DB error (get_or_create_user): {e}")
        
        # Fallback: in-memory
        if email not in self._memory["users"]:
            self._memory["users"][email] = {
                "id": hashlib.md5(email.encode()).hexdigest(),
                "email": email,
                "display_name": display_name or email.split("@")[0],
                "giving_profile": {},
                "preferences": {},
            }
        return self._memory["users"][email]
    
    def update_giving_profile(self, user_id: str, profile: dict) -> bool:
        """Update donor's giving profile (causes, budget, geography, philosophy)."""
        if self.connected:
            try:
                self.client.table("users").update({"giving_profile": profile}).eq("id", user_id).execute()
                return True
            except Exception as e:
                print(f"DB error (update_giving_profile): {e}")
        return False
    
    def get_giving_profile(self, user_id: str) -> dict:
        """Retrieve donor's giving profile."""
        if self.connected:
            try:
                result = self.client.table("users").select("giving_profile").eq("id", user_id).execute()
                if result.data and result.data[0].get("giving_profile"):
                    profile = result.data[0]["giving_profile"]
                    if isinstance(profile, str):
                        return json.loads(profile)
                    return profile
            except Exception as e:
                print(f"DB error (get_giving_profile): {e}")
        return {}
    
    # ══════════════════════════════════════════
    # PORTFOLIO MANAGEMENT
    # ══════════════════════════════════════════
    
    def save_portfolio(self, user_id: str, grants: list) -> bool:
        """Save/replace entire portfolio for a user."""
        if self.connected:
            try:
                # Delete existing grants for this user
                self.client.table("portfolio_grants").delete().eq("user_id", user_id).execute()
                # Insert new grants — map UI field names to database columns
                if grants:
                    rows = []
                    for g in grants:
                        rows.append({
                            "user_id": user_id,
                            "name": g.get("name", ""),
                            "organization": g.get("org", g.get("organization", "")),
                            "geography": g.get("geography", ""),
                            "sector": g.get("sector", ""),
                            "sector_code": g.get("sector_code", ""),
                            "budget": g.get("budget", ""),
                            "status": g.get("status", "Active - On track"),
                            "milestones": g.get("milestones", ""),
                            "notes": g.get("notes", ""),
                        })
                    self.client.table("portfolio_grants").insert(rows).execute()
                return True
            except Exception as e:
                print(f"DB error (save_portfolio): {e}")
        
        # Fallback
        self._memory["portfolio_grants"][user_id] = grants
        return True
    
    def load_portfolio(self, user_id: str) -> list:
        """Load all portfolio grants for a user."""
        if self.connected:
            try:
                result = self.client.table("portfolio_grants").select("*").eq("user_id", user_id).order("created_at").execute()
                if result.data:
                    # Map database column names back to UI field names
                    grants = []
                    for row in result.data:
                        grants.append({
                            "id": row.get("id", ""),
                            "name": row.get("name", ""),
                            "org": row.get("organization", ""),
                            "geography": row.get("geography", ""),
                            "sector": row.get("sector", ""),
                            "sector_code": row.get("sector_code", ""),
                            "budget": row.get("budget", ""),
                            "status": row.get("status", ""),
                            "milestones": row.get("milestones", ""),
                            "notes": row.get("notes", ""),
                        })
                    return grants
                return []
            except Exception as e:
                print(f"DB error (load_portfolio): {e}")
        
        return self._memory["portfolio_grants"].get(user_id, [])
    
    def update_grant(self, grant_id: str, updates: dict) -> bool:
        """Update a specific grant."""
        if self.connected:
            try:
                self.client.table("portfolio_grants").update(updates).eq("id", grant_id).execute()
                return True
            except Exception as e:
                print(f"DB error (update_grant): {e}")
        return False
    
    # ══════════════════════════════════════════
    # EVALUATION STORAGE
    # ══════════════════════════════════════════
    
    @staticmethod
    def _clean_for_json(obj):
        """Recursively convert non-serializable objects to strings for JSONB storage."""
        if isinstance(obj, dict):
            return {k: Database._clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [Database._clean_for_json(v) for v in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)
    
    def save_evaluation(self, user_id: str, proposal_name: str, proposal_text: str,
                        sector: str, geography: str, recommendation: str,
                        evaluation_text: str, tool_calls: list = None) -> bool:
        """Store a proposal evaluation result."""
        record = {
            "user_id": user_id,
            "proposal_name": proposal_name,
            "proposal_text": proposal_text[:3000],
            "sector": sector,
            "geography": geography,
            "recommendation": recommendation,
            "evaluation_text": evaluation_text,
            "tool_calls": self._clean_for_json(tool_calls or []),
        }
        if self.connected:
            try:
                self.client.table("evaluations").insert(record).execute()
                return True
            except Exception as e:
                print(f"DB error (save_evaluation): {e}")
        
        self._memory["evaluations"].append(record)
        return True
    
    def get_evaluations(self, user_id: str, limit: int = 20) -> list:
        """Retrieve recent evaluations for a user."""
        if self.connected:
            try:
                result = (self.client.table("evaluations")
                          .select("*")
                          .eq("user_id", user_id)
                          .order("created_at", desc=True)
                          .limit(limit)
                          .execute())
                return result.data or []
            except Exception as e:
                print(f"DB error (get_evaluations): {e}")
        
        return [e for e in self._memory["evaluations"] if e.get("user_id") == user_id][-limit:]
    
    # ══════════════════════════════════════════
    # REPORT ANALYSES
    # ══════════════════════════════════════════
    
    def save_report_analysis(self, user_id: str, grant_id: str, grant_name: str,
                             report_text: str, analysis_text: str) -> bool:
        """Store a grantee report analysis."""
        record = {
            "user_id": user_id,
            "grant_name": grant_name,
            "report_text": report_text[:3000],
            "analysis_text": analysis_text,
        }
        # Only include grant_id if it's a valid non-empty value
        if grant_id and grant_id != "":
            record["grant_id"] = grant_id
        if self.connected:
            try:
                self.client.table("report_analyses").insert(record).execute()
                return True
            except Exception as e:
                print(f"DB error (save_report_analysis): {e}")
        
        key = f"{user_id}:{grant_name}"
        self._memory["report_analyses"][key] = record
        return True
    
    def get_report_analyses(self, user_id: str, grant_name: str = None) -> list:
        """Retrieve report analyses, optionally filtered by grant."""
        if self.connected:
            try:
                query = self.client.table("report_analyses").select("*").eq("user_id", user_id)
                if grant_name:
                    query = query.eq("grant_name", grant_name)
                result = query.order("created_at", desc=True).limit(20).execute()
                return result.data or []
            except Exception as e:
                print(f"DB error (get_report_analyses): {e}")
        
        analyses = list(self._memory["report_analyses"].values())
        if grant_name:
            analyses = [a for a in analyses if a.get("grant_name") == grant_name]
        return analyses
    
    # ══════════════════════════════════════════
    # CONVERSATION HISTORY
    # ══════════════════════════════════════════
    
    def save_conversation(self, user_id: str, mode: str, messages: list, 
                          conversation_id: str = None) -> str:
        """Save or update a conversation. Returns conversation ID."""
        if self.connected:
            try:
                # Generate title from first user message
                title = "New conversation"
                for msg in messages:
                    if msg.get("role") == "user":
                        title = msg["content"][:80]
                        break
                
                clean_messages = self._clean_for_json(messages)
                
                if conversation_id:
                    self.client.table("conversations").update({
                        "messages": clean_messages,
                        "title": title,
                    }).eq("id", conversation_id).execute()
                    return conversation_id
                else:
                    result = self.client.table("conversations").insert({
                        "user_id": user_id,
                        "mode": mode,
                        "title": title,
                        "messages": clean_messages,
                    }).execute()
                    return result.data[0]["id"] if result.data else None
            except Exception as e:
                print(f"DB error (save_conversation): {e}")
        
        # Fallback
        key = f"{user_id}:{mode}"
        self._memory["conversations"][key] = messages
        return key
    
    def load_recent_conversations(self, user_id: str, mode: str, limit: int = 5) -> list:
        """Load recent conversations for a user in a specific mode."""
        if self.connected:
            try:
                result = (self.client.table("conversations")
                          .select("*")
                          .eq("user_id", user_id)
                          .eq("mode", mode)
                          .order("updated_at", desc=True)
                          .limit(limit)
                          .execute())
                convos = result.data or []
                # Parse messages JSON
                for c in convos:
                    if isinstance(c.get("messages"), str):
                        c["messages"] = json.loads(c["messages"])
                return convos
            except Exception as e:
                print(f"DB error (load_recent_conversations): {e}")
        
        key = f"{user_id}:{mode}"
        msgs = self._memory["conversations"].get(key, [])
        return [{"messages": msgs, "title": "Previous conversation"}] if msgs else []
    
    def get_context_summary(self, user_id: str, mode: str) -> str:
        """Build a context summary from recent conversations for the agent."""
        recent = self.load_recent_conversations(user_id, mode, limit=3)
        if not recent:
            return ""
        
        summary_parts = []
        for convo in recent[:3]:
            msgs = convo.get("messages", [])
            # Extract key exchanges (first user msg + first assistant response summary)
            for msg in msgs[:4]:  # First 2 exchanges max
                role = msg.get("role", "")
                content = msg.get("content", "")[:200]
                if role == "user":
                    summary_parts.append(f"User asked: {content}")
                elif role == "assistant":
                    summary_parts.append(f"You responded about: {content}")
        
        if summary_parts:
            return "CONTEXT FROM PREVIOUS SESSIONS:\n" + "\n".join(summary_parts[:6]) + "\n\n"
        return ""
    
    # ══════════════════════════════════════════
    # DATA CACHE (DHIS2, web research)
    # ══════════════════════════════════════════
    
    def get_cached_data(self, cache_key: str) -> dict:
        """Retrieve cached data if not expired."""
        if self.connected:
            try:
                result = (self.client.table("data_cache")
                          .select("*")
                          .eq("cache_key", cache_key)
                          .gt("expires_at", datetime.now(timezone.utc).isoformat())
                          .execute())
                if result.data:
                    data = result.data[0]["data"]
                    return json.loads(data) if isinstance(data, str) else data
            except Exception as e:
                print(f"DB error (get_cached_data): {e}")
        
        # Fallback: check in-memory cache
        cached = self._memory["data_cache"].get(cache_key)
        if cached and cached.get("expires_at", "") > datetime.now(timezone.utc).isoformat():
            return cached.get("data")
        return None
    
    def set_cached_data(self, cache_key: str, data: dict, source: str = "dhis2", ttl_hours: int = 24) -> bool:
        """Store data in cache with TTL."""
        expires = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()
        
        if self.connected:
            try:
                clean_data = self._clean_for_json(data)
                self.client.table("data_cache").upsert({
                    "cache_key": cache_key,
                    "data": clean_data,
                    "source": source,
                    "ttl_hours": ttl_hours,
                    "expires_at": expires,
                }, on_conflict="cache_key").execute()
                return True
            except Exception as e:
                print(f"DB error (set_cached_data): {e}")
        
        # Fallback
        self._memory["data_cache"][cache_key] = {"data": data, "expires_at": expires}
        return True
    
    def make_cache_key(self, source: str, category: str, geography: str) -> str:
        """Generate a consistent cache key."""
        return f"{source}:{category}:{geography.lower().replace(' ', '_')}"
    
    # ══════════════════════════════════════════
    # BOARD REPORTS
    # ══════════════════════════════════════════
    
    def save_board_report(self, user_id: str, period: str, report_text: str, 
                          portfolio_snapshot: list) -> bool:
        """Store a generated board report."""
        record = {
            "user_id": user_id,
            "period": period,
            "report_text": report_text,
            "portfolio_snapshot": self._clean_for_json(portfolio_snapshot),
        }
        if self.connected:
            try:
                self.client.table("board_reports").insert(record).execute()
                return True
            except Exception as e:
                print(f"DB error (save_board_report): {e}")
        
        self._memory["board_reports"].append(record)
        return True
    
    def get_board_reports(self, user_id: str, limit: int = 4) -> list:
        """Retrieve recent board reports for quarter-over-quarter comparison."""
        if self.connected:
            try:
                result = (self.client.table("board_reports")
                          .select("*")
                          .eq("user_id", user_id)
                          .order("created_at", desc=True)
                          .limit(limit)
                          .execute())
                return result.data or []
            except Exception as e:
                print(f"DB error (get_board_reports): {e}")
        
        return [r for r in self._memory["board_reports"] if r.get("user_id") == user_id][-limit:]
    
    # ══════════════════════════════════════════
    # UTILITY
    # ══════════════════════════════════════════
    
    def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries. Returns count of deleted rows."""
        if self.connected:
            try:
                result = (self.client.table("data_cache")
                          .delete()
                          .lt("expires_at", datetime.now(timezone.utc).isoformat())
                          .execute())
                return len(result.data) if result.data else 0
            except Exception as e:
                print(f"DB error (cleanup_expired_cache): {e}")
        return 0
    
    def get_status(self) -> dict:
        """Return database connection status and stats."""
        status = {
            "connected": self.connected,
            "backend": "Supabase" if self.connected else "In-memory (session only)",
        }
        if self.connected:
            try:
                users = self.client.table("users").select("id", count="exact").execute()
                grants = self.client.table("portfolio_grants").select("id", count="exact").execute()
                evals = self.client.table("evaluations").select("id", count="exact").execute()
                cache = self.client.table("data_cache").select("id", count="exact").execute()
                status["users"] = users.count or 0
                status["grants"] = grants.count or 0
                status["evaluations"] = evals.count or 0
                status["cached_queries"] = cache.count or 0
            except Exception:
                pass
        return status
