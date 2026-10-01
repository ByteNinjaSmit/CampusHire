import { api, apiFetch, publicApi, refreshSession } from "../client";
import type {
  CompanyRegisterRequest,
  LoginRequest,
  MessageResponse,
  Me,
  StudentRegisterRequest,
  TokenResponse,
} from "../types";
import { emitSession, setAccessToken } from "@/lib/auth/token-store";

export const authApi = {
  registerStudent: (body: StudentRegisterRequest) => publicApi.post<MessageResponse>("/auth/register/student", body),
  registerCompany: (body: CompanyRegisterRequest) => publicApi.post<MessageResponse>("/auth/register/company", body),
  async login(body: LoginRequest) {
    const data = await publicApi.post<TokenResponse>("/auth/login", body);
    setAccessToken(data.access_token);
    emitSession(data.user);
    return data;
  },
  refresh: () => refreshSession(),
  logout: () =>
    apiFetch<void>("/auth/logout", { method: "POST", headers: { "X-Requested-With": "campushire" }, anonymous: true }),
  verifyEmail: (token: string) => publicApi.post<MessageResponse>("/auth/verify-email", { token }),
  resendVerification: (email: string) => publicApi.post<MessageResponse>("/auth/resend-verification", { email }),
  forgotPassword: (email: string) => publicApi.post<MessageResponse>("/auth/forgot-password", { email }),
  resetPassword: (token: string, new_password: string) => publicApi.post<MessageResponse>("/auth/reset-password", { token, new_password }),
  me: () => api.get<Me>("/auth/me"),
  changePassword: (current_password: string, new_password: string) =>
    api.post<MessageResponse>("/auth/change-password", { current_password, new_password }),
};
