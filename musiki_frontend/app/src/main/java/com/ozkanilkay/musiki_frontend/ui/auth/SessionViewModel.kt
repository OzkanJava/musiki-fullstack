package com.ozkanilkay.musiki_frontend.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ozkanilkay.musiki_frontend.data.model.UserResponse
import com.ozkanilkay.musiki_frontend.data.remote.ApiService
import com.ozkanilkay.musiki_frontend.data.remote.TokenManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import javax.inject.Inject

sealed class SessionState {
    data object Loading : SessionState()
    data object Authenticated : SessionState()
    data object Unauthenticated : SessionState()
}

/**
 * Uygulama açıldığında DataStore'daki token'ı sunucuya doğrulayarak
 * oturum durumunu belirler.
 *
 * Ayrıca token'ı observe eder — TokenAuthenticator forced logout yaptığında
 * (token temizlenince) otomatik olarak Unauthenticated state'e geçer.
 */
@HiltViewModel
class SessionViewModel @Inject constructor(
    private val api: ApiService,
    private val tokenManager: TokenManager,
) : ViewModel() {

    private val _sessionState = MutableStateFlow<SessionState>(SessionState.Loading)
    val sessionState = _sessionState.asStateFlow()

    private val _currentUser = MutableStateFlow<UserResponse?>(null)
    val currentUser = _currentUser.asStateFlow()

    init {
        verifySession()
        observeTokenForForcedLogout()
    }

    private fun verifySession() {
        viewModelScope.launch {
            val token = tokenManager.accessToken.firstOrNull()

            if (token.isNullOrBlank()) {
                _sessionState.value = SessionState.Unauthenticated
                return@launch
            }

            // Token var — sunucuya sor. 5sn timeout: backend kapalıysa
            // kullanıcı beyaz ekranda kalmasın, hızlıca Login'e düşsün.
            val response = withTimeoutOrNull(5_000) {
                runCatching { api.getMe() }.getOrNull()
            }

            if (response?.isSuccessful == true) {
                _currentUser.value = response.body()
                _sessionState.value = SessionState.Authenticated
            } else {
                _sessionState.value = SessionState.Unauthenticated
            }
        }
    }

    /**
     * TokenAuthenticator forced logout yaptığında token null olur.
     * Bu observer authenticated durumda token kaybolursa login'e atar.
     */
    private fun observeTokenForForcedLogout() {
        viewModelScope.launch {
            tokenManager.accessToken
                .map { it.isNullOrBlank() }
                .distinctUntilChanged()
                .collect { isBlank ->
                    if (isBlank && _sessionState.value == SessionState.Authenticated) {
                        _currentUser.value = null
                        _sessionState.value = SessionState.Unauthenticated
                    }
                }
        }
    }
}
