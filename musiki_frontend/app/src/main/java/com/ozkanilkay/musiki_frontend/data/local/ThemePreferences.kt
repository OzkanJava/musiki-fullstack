package com.ozkanilkay.musiki_frontend.data.local

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.ozkanilkay.musiki_frontend.ui.theme.ThemeMode
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.themeDataStore by preferencesDataStore(name = "musiki_theme")

@Singleton
class ThemePreferences @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val ds = context.themeDataStore

    val themeMode: Flow<ThemeMode> = ds.data.map { prefs ->
        when (prefs[THEME_KEY]) {
            "dark"   -> ThemeMode.DARK
            "light"  -> ThemeMode.LIGHT
            "system" -> ThemeMode.SYSTEM
            else     -> ThemeMode.DARK
        }
    }

    suspend fun setThemeMode(mode: ThemeMode) {
        ds.edit { prefs ->
            prefs[THEME_KEY] = when (mode) {
                ThemeMode.DARK   -> "dark"
                ThemeMode.LIGHT  -> "light"
                ThemeMode.SYSTEM -> "system"
            }
        }
    }

    companion object {
        private val THEME_KEY = stringPreferencesKey("theme_mode")
    }
}
