package com.ozkanilkay.musiki_frontend.ui.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ozkanilkay.musiki_frontend.data.local.ThemePreferences
import com.ozkanilkay.musiki_frontend.data.model.ListenHistoryDto
import com.ozkanilkay.musiki_frontend.data.model.RequestArtistRequest
import com.ozkanilkay.musiki_frontend.data.model.UserResponse
import com.ozkanilkay.musiki_frontend.data.remote.ApiService
import com.ozkanilkay.musiki_frontend.data.remote.TokenManager
import com.ozkanilkay.musiki_frontend.ui.theme.ThemeMode
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProfileUiState(
    val isLoading: Boolean = true,
    val user: UserResponse? = null,
    val history: List<ListenHistoryDto> = emptyList(),
    val requestArtistLoading: Boolean = false,
    val requestArtistSuccess: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val api: ApiService,
    private val tokenManager: TokenManager,
    private val themePreferences: ThemePreferences,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState = _uiState.asStateFlow()

    val themeMode = themePreferences.themeMode
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), ThemeMode.DARK)

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                val meResp = api.getMe()
                val histResp = api.getHistory()

                _uiState.update {
                    it.copy(
                        isLoading = false,
                        user = if (meResp.isSuccessful) meResp.body() else null,
                        history = if (histResp.isSuccessful) histResp.body()?.results ?: emptyList() else emptyList(),
                    )
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }

    fun setThemeMode(mode: ThemeMode) {
        viewModelScope.launch {
            themePreferences.setThemeMode(mode)
        }
    }

    fun requestArtist(bio: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(requestArtistLoading = true, error = null) }
            try {
                val resp = api.requestArtist(RequestArtistRequest(bio))
                if (resp.isSuccessful) {
                    _uiState.update { it.copy(requestArtistLoading = false, requestArtistSuccess = true) }
                    load() // Kullanıcı bilgisini yenile
                } else {
                    _uiState.update { it.copy(requestArtistLoading = false, error = "Başvuru başarısız") }
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(requestArtistLoading = false, error = e.message) }
            }
        }
    }

    fun logout(onLoggedOut: () -> Unit) {
        viewModelScope.launch {
            tokenManager.clearTokens()
            onLoggedOut()
        }
    }
}
