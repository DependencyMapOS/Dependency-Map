export const OTP_LENGTH = 6;

export function normalizeOtp(raw: string): string {
  return raw.replace(/\D/g, "").slice(0, OTP_LENGTH);
}
