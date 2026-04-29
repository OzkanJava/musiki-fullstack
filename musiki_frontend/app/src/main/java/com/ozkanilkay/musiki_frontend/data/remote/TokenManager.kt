package com.ozkanilkay.musiki_frontend.data.remote

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences>
        by preferencesDataStore(name = "musiki_prefs")

@Singleton
class TokenManager @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val ds = context.dataStore

    val accessToken: Flow<String?> = ds.data.map { it[ACCESS_KEY] }
    val refreshToken: Flow<String?> = ds.data.map { it[REFRESH_KEY] }

    suspend fun saveTokens(access: String, refresh: String) {
        ds.edit {
            it[ACCESS_KEY] = access
            it[REFRESH_KEY] = refresh
        }
    }

    suspend fun saveAccessToken(access: String) {
        ds.edit { it[ACCESS_KEY] = access }
    }

    suspend fun clearTokens() {
        ds.edit { it.clear() }
    }

    companion object {
        private val ACCESS_KEY  = stringPreferencesKey("access_token")
        private val REFRESH_KEY = stringPreferencesKey("refresh_token")
    }
}
