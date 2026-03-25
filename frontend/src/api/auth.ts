import api from "./http";
import type { AuthUser, LoginResponse } from "../types";


export function login(payload: { email: string; password: string }) {
  return api.post<LoginResponse>("/api/v1/auth/login", payload);
}

export function getCurrentUser() {
  return api.get<AuthUser>("/api/v1/auth/me");
}
