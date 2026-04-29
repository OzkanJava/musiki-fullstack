package com.ozkanilkay.musiki_frontend.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

// ── Musiki Brand Palette ─────────────────────────────────────────────────────
// Primary: Teal #85E0D5   Secondary: Peach #FFBE8F

data class MusikiColorPalette(
    val background: Color,
    val surface: Color,
    val surfaceHigh: Color,
    val primary: Color,
    val primaryDim: Color,
    val secondary: Color,
    val secondaryDim: Color,
    val onPrimary: Color,
    val onSecondary: Color,
    val textPrimary: Color,
    val textSecondary: Color,
    val textDisabled: Color,
    val error: Color,
    val success: Color,
    val white: Color,
    val outline: Color,
    val gray: Color,
    val darkGray: Color,
    val divider: Color,
)

// ── Dark Theme Colors ────────────────────────────────────────────────────────
val DarkMusikiPalette = MusikiColorPalette(
    background    = Color(0xFF0D0D0D),
    surface       = Color(0xFF1A1A1A),
    surfaceHigh   = Color(0xFF252527),
    primary       = Color(0xFF85E0D5),   // Teal
    primaryDim    = Color(0xFF5BB8AD),
    secondary     = Color(0xFFFF9B57),   // Vivid orange
    secondaryDim  = Color(0xFFD47A3E),
    onPrimary     = Color(0xFF0D0D0D),
    onSecondary   = Color(0xFF0D0D0D),
    textPrimary   = Color(0xFFE8E8E8),
    textSecondary = Color(0xFF9E9E9E),
    textDisabled  = Color(0xFF5E5E5E),
    error         = Color(0xFFCF6679),
    success       = Color(0xFF22C55E),
    white         = Color(0xFFFFFFFF),
    outline       = Color(0xFF3D3D3D),
    gray          = Color(0xFF2A2A2A),
    darkGray      = Color(0xFF1A1A1A),
    divider       = Color(0xFF2A2A2A),
)

// ── Light Theme Colors ───────────────────────────────────────────────────────
val LightMusikiPalette = MusikiColorPalette(
    background    = Color(0xFFF5F5F5),
    surface       = Color(0xFFFFFFFF),
    surfaceHigh   = Color(0xFFEEEEEE),
    primary       = Color(0xFF4DB8AC),   // Deeper teal for contrast on light
    primaryDim    = Color(0xFF85E0D5),
    secondary     = Color(0xFFE8802A),   // Vivid orange for contrast on light
    secondaryDim  = Color(0xFFB85F1F),
    onPrimary     = Color(0xFFFFFFFF),
    onSecondary   = Color(0xFFFFFFFF),
    textPrimary   = Color(0xFF1A1A1A),
    textSecondary = Color(0xFF666666),
    textDisabled  = Color(0xFFB0B0B0),
    error         = Color(0xFFB00020),
    success       = Color(0xFF1B9E4B),
    white         = Color(0xFFFFFFFF),
    outline       = Color(0xFFD0D0D0),
    gray          = Color(0xFFE0E0E0),
    darkGray      = Color(0xFFD0D0D0),
    divider       = Color(0xFFE0E0E0),
)

// ── CompositionLocal ─────────────────────────────────────────────────────────
val LocalMusikiColors = staticCompositionLocalOf { DarkMusikiPalette }

/** Theme-aware color accessor — use `Musiki.colors.primary`, etc. */
object Musiki {
    val colors: MusikiColorPalette
        @Composable get() = LocalMusikiColors.current
}

// ── Legacy aliases (kept for backward compat during migration) ───────────────
// These always point to dark palette values; prefer Musiki.colors in @Composable scope.
val MusikiBlack         = DarkMusikiPalette.background
val MusikiDarkGray      = DarkMusikiPalette.darkGray
val MusikiGray          = DarkMusikiPalette.gray
val MusikiLightGray     = DarkMusikiPalette.outline
val MusikiPrimary       = DarkMusikiPalette.primary
val MusikiPrimaryDim    = DarkMusikiPalette.primaryDim
val MusikiSecondary     = DarkMusikiPalette.secondary
val MusikiOnPrimary     = DarkMusikiPalette.onPrimary
val MusikiTextPrimary   = DarkMusikiPalette.textPrimary
val MusikiTextSecondary = DarkMusikiPalette.textSecondary
val MusikiTextDisabled  = DarkMusikiPalette.textDisabled
val MusikiError         = DarkMusikiPalette.error
val MusikiSuccess       = DarkMusikiPalette.success
val MusikiWhite         = DarkMusikiPalette.white
val MusikiSurface       = DarkMusikiPalette.surface
val MusikiSurfaceHigh   = DarkMusikiPalette.surfaceHigh
