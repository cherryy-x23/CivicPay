const TOKEN_KEY = "civicpay_access_token";
const USER_KEY = "civicpay_user";

export function saveAuth(accessToken, user) {
  localStorage.setItem(TOKEN_KEY, accessToken);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getCurrentUser() {
  const user = localStorage.getItem(USER_KEY);

  if (!user) {
    return null;
  }

  try {
    return JSON.parse(user);
  } catch {
    return null;
  }
}

export function isAuthenticated() {
  return Boolean(getAccessToken());
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getAuthHeaders() {
  const token = getAccessToken();

  if (!token) {
    return {};
  }

  return {
    Authorization: `Bearer ${token}`,
  };
}