package com.ozkanilkay.musiki_frontend.data.remote

import android.util.Log
import com.squareup.moshi.Moshi
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.runBlocking
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody

/**
 * 401 geldiğinde:
 *   1) Refresh token ile yeni access token almayı dener
 *   2) Refresh da fail ederse, kayıtlı credentials ile otomatik login dener
 *   3) O da fail ederse (şifre değişmiş) → null döner → SessionViewModel logout tetikler
 */
class TokenAuthenticator(
    private val tokenManager: TokenManager,
    private val credentialManager: CredentialManager,
    private val moshi: Moshi,
    private val okHttpClientProvider: () -> OkHttpClient,
) : Authenticator {

    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    // Aynı anda birden fazla 401 geldiğinde tek refresh yapılması için lock
    private val lock = Any()

    override fun authenticate(route: Route?, response: Response): Request? {
        // Sonsuz döngüyü önle — bu istek zaten retry ise bırak
        if (response.request.header("X-Auth-Retry") != null) {
            Log.w("TokenAuthenticator", "Retry request de 401 aldı — logout")
            forceLogout()
            return null
        }

        synchronized(lock) {
            // Başka thread zaten token yenilediyse, yeni token'ı dene
            val currentToken = runBlocking { tokenManager.accessToken.firstOrNull() }
            val failedToken = response.request.header("Authorization")?.removePrefix("Bearer ")

            if (currentToken != null && currentToken != failedToken) {
                // Token zaten yenilendi, bu token ile tekrar dene
                return response.request.newBuilder()
                    .header("Authorization", "Bearer $currentToken")
                    .header("X-Auth-Retry", "true")
                    .build()
            }

            // 1. Refresh token dene
            val newAccess = tryRefreshToken()
            if (newAccess != null) {
                return response.request.newBuilder()
                    .header("Authorization", "Bearer $newAccess")
                    .header("X-Auth-Retry", "true")
                    .build()
            }

            // 2. Kayıtlı credentials ile otomatik login dene
            val loginAccess = tryAutoLogin()
            if (loginAccess != null) {
                return response.request.newBuilder()
                    .header("Authorization", "Bearer $loginAccess")
                    .header("X-Auth-Retry", "true")
                    .build()
            }

            // 3. Hiçbiri işe yaramadı — şifre değişmiş, logout
            forceLogout()
            return null
        }
    }

    private fun tryRefreshToken(): String? {
        val refresh = runBlocking { tokenManager.refreshToken.firstOrNull() }
        if (refresh.isNullOrBlank()) return null

        return try {
            val body = """{"refresh":"$refresh"}""".toRequestBody(jsonMediaType)
            val request = Request.Builder()
                .url(getBaseUrl() + "api/auth/token/refresh/")
                .post(body)
                .build()

            val resp = okHttpClientProvider().newCall(request).execute()
            if (resp.isSuccessful) {
                val json = resp.body?.string() ?: return null
                val adapter = moshi.adapter(RefreshResult::class.java)
                val result = adapter.fromJson(json) ?: return null
                runBlocking { tokenManager.saveAccessToken(result.access) }
                Log.d("TokenAuthenticator", "Token refresh başarılı")
                result.access
            } else {
                Log.w("TokenAuthenticator", "Refresh token fail: ${resp.code}")
                null
            }
        } catch (e: Exception) {
            Log.e("TokenAuthenticator", "Refresh exception", e)
            null
        }
    }

    private fun tryAutoLogin(): String? {
        if (!credentialManager.hasCredentials()) return null

        val username = credentialManager.getUsername()!!
        val password = credentialManager.getPassword()!!

        return try {
            val body = """{"username":"$username","password":"$password"}"""
                .toRequestBody(jsonMediaType)
            val request = Request.Builder()
                .url(getBaseUrl() + "api/auth/token/")
                .post(body)
                .build()

            val resp = okHttpClientProvider().newCall(request).execute()
            if (resp.isSuccessful) {
                val json = resp.body?.string() ?: return null
                val adapter = moshi.adapter(LoginResult::class.java)
                val result = adapter.fromJson(json) ?: return null
                runBlocking { tokenManager.saveTokens(result.access, result.refresh) }
                Log.d("TokenAuthenticator", "Auto-login başarılı")
                result.access
            } else {
                // Şifre değişmiş
                Log.w("TokenAuthenticator", "Auto-login fail: ${resp.code} — şifre değişmiş")
                credentialManager.clearCredentials()
                null
            }
        } catch (e: Exception) {
            Log.e("TokenAuthenticator", "Auto-login exception", e)
            null
        }
    }

    private fun forceLogout() {
        runBlocking {
            tokenManager.clearTokens()
        }
        credentialManager.clearCredentials()
        Log.w("TokenAuthenticator", "Forced logout — login ekranına yönlendirilecek")
    }

    private fun getBaseUrl(): String {
        // BuildConfig'e erişmeden, interceptor'daki mevcut request URL'inden base alıyoruz
        // Ama burada static kullanmak daha güvenli
        return com.ozkanilkay.musiki_frontend.BuildConfig.BASE_URL
    }

    // Sadece JSON parse için minimal data class'lar
    @com.squareup.moshi.JsonClass(generateAdapter = true)
    data class RefreshResult(val access: String)

    @com.squareup.moshi.JsonClass(generateAdapter = true)
    data class LoginResult(val access: String, val refresh: String)
}
