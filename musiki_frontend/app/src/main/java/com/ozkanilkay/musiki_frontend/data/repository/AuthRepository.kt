package com.ozkanilkay.musiki_frontend.data.repository

import com.ozkanilkay.musiki_frontend.data.model.*
import com.ozkanilkay.musiki_frontend.data.remote.ApiService
import com.ozkanilkay.musiki_frontend.data.remote.CredentialManager
import com.ozkanilkay.musiki_frontend.data.remote.TokenManager
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

sealed class AuthResult<out T> {
    data class Success<T>(val data: T) : AuthResult<T>()
    data class Error(val message: String) : AuthResult<Nothing>()
}

@Singleton
class AuthRepository @Inject constructor(
    private val api: ApiService,
    private val tokenManager: TokenManager,
    private val credentialManager: CredentialManager,
) {
    suspend fun login(username: String, password: String): AuthResult<UserResponse> {
        return try {
            val resp = api.login(LoginRequest(username, password))
            if (resp.isSuccessful) {
                val tokens = resp.body()!!
                tokenManager.saveTokens(tokens.access, tokens.refresh)
                credentialManager.saveCredentials(username, password)
                val me = api.getMe()
                if (me.isSuccessful) AuthResult.Success(me.body()!!)
                else AuthResult.Error("Kullanıcı bilgisi alınamadı")
            } else {
                AuthResult.Error("Kullanıcı adı veya şifre hatalı")
            }
        } catch (e: IOException) {
            AuthResult.Error("Sunucu aktif değil veya ulaşılamıyor")
        } catch (e: Exception) {
            AuthResult.Error("Bir hata oluştu: ${e.message}")
        }
    }

    suspend fun register(
        username: String,
        email: String,
        password: String,
        passwordConfirm: String,
    ): AuthResult<UserResponse> {
        return try {
            val resp = api.register(RegisterRequest(username, email, password, passwordConfirm))
            if (resp.isSuccessful) {
                // Kayıt başarılı → otomatik login
                login(username, password)
            } else {
                val errorBody = resp.errorBody()?.string() ?: "Kayıt başarısız"
                AuthResult.Error(errorBody)
            }
        } catch (e: IOException) {
            AuthResult.Error("Sunucu aktif değil veya ulaşılamıyor")
        } catch (e: Exception) {
            AuthResult.Error("Bir hata oluştu: ${e.message}")
        }
    }

    suspend fun logout() {
        tokenManager.clearTokens()
        credentialManager.clearCredentials()
    }

    fun accessTokenFlow() = tokenManager.accessToken
}
