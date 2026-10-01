"use client";

import { useMutation } from "@tanstack/react-query";
import { authApi } from "../endpoints/auth";
import type { CompanyRegisterRequest, LoginRequest, StudentRegisterRequest } from "../types";

export const useLogin = () => useMutation({ mutationFn: (body: LoginRequest) => authApi.login(body) });
export const useRegisterStudent = () => useMutation({ mutationFn: (body: StudentRegisterRequest) => authApi.registerStudent(body) });
export const useRegisterCompany = () => useMutation({ mutationFn: (body: CompanyRegisterRequest) => authApi.registerCompany(body) });
export const useVerifyEmail = () => useMutation({ mutationFn: (token: string) => authApi.verifyEmail(token) });
export const useResendVerification = () => useMutation({ mutationFn: (email: string) => authApi.resendVerification(email) });
export const useForgotPassword = () => useMutation({ mutationFn: (email: string) => authApi.forgotPassword(email) });
export const useResetPassword = () =>
  useMutation({ mutationFn: (v: { token: string; new_password: string }) => authApi.resetPassword(v.token, v.new_password) });
export const useChangePassword = () =>
  useMutation({ mutationFn: (v: { current_password: string; new_password: string }) => authApi.changePassword(v.current_password, v.new_password) });
