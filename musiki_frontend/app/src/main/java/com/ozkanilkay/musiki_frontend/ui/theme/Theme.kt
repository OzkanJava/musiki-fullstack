package com.ozkanilkay.musiki_frontend.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

// ── Theme Mode ───────────────────────────────────────────────────────────────
enum class ThemeMode { DARK, LIGHT, SYSTEM }

// ── Material3 Color Schemes ──────────────────────────────────────────────────
private fun musikiDarkColorScheme(p: MusikiColorPalette) = darkColorScheme(
    primary          = p.primary,
    onPrimary        = p.onPrimary,
    primaryContainer = p.primaryDim,
    secondary        = p.secondary,
    onSecondary      = p.onSecondary,
    background       = p.background,
    onBackground     = p.textPrimary,
    surface          = p.surface,
    onSurface        = p.textPrimary,
    surfaceVariant   = p.gray,
    onSurfaceVariant = p.textSecondary,
    error            = p.error,
    onError          = p.white,
    outline          = p.outline,
)

private fun musikiLightColorScheme(p: MusikiColorPalette) = lightColorScheme(
    primary          = p.primary,
    onPrimary        = p.onPrimary,
    primaryContainer = p.primaryDim,
    secondary        = p.secondary,
    onSecondary      = p.onSecondary,
    background       = p.background,
    onBackground     = p.textPrimary,
    surface          = p.surface,
    onSurface        = p.textPrimary,
    surfaceVariant   = p.gray,
    onSurfaceVariant = p.textSecondary,
    error            = p.error,
    onError          = p.white,
    outline          = p.outline,
)

// ── Theme Composable ─────────────────────────────────────────────────────────
@Composable
fun MusikiTheme(
    themeMode: ThemeMode = ThemeMode.DARK,
    content: @Composable () -> Unit,
) {
    val isDark = when (themeMode) {
        ThemeMode.DARK   -> true
        ThemeMode.LIGHT  -> false
        ThemeMode.SYSTEM -> isSystemInDarkTheme()
    }

    val palette = if (isDark) DarkMusikiPalette else LightMusikiPalette
    val colorScheme = if (isDark) musikiDarkColorScheme(palette) else musikiLightColorScheme(palette)

    // Status bar color
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = palette.background.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !isDark
        }
    }

    CompositionLocalProvider(LocalMusikiColors provides palette) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography  = MusikiTypography,
            content     = content,
        )
    }
}
