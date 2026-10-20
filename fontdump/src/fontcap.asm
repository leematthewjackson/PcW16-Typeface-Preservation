; SPDX-License-Identifier: GPL-3.0-only
; Copyright (C) 2026 Lee Matthew Jackson - PcW16ers.net & leematthewjackson.com
; ============================================================================
; FONTCAP -- PcW16 Typeface Preservation: discover and capture the typefaces
;            installed on this PcW16
; ============================================================================
; Writes FONTLIST.TXT (the installed fonts) and, for every font, style and
; size the user chooses, one F<id><style><size>.FD6 file (docs/FORMAT.md,
; version 6).
;
; WHAT IT DOES
;   1. Menu: "Capture fonts", "List fonts only" or "Cancel".
;   2. Reads the typeface list (os_typo_getlist: ID, styles, RTF family,
;      name per entry), with FONTDMP4/5's guarded os_typo_init.
;   3. Probes every listed font at every typo size (6 8 10 11 12 14 18 24
;      36 72): os_typo_def in a free slot, cleared at once. A=2 ("size out
;      of range") = size not available.
;   4. Writes FONTLIST.TXT (never overwritten: if it exists it is left
;      alone), then shows one alert per font: name, ID, RTF family, styles,
;      available sizes. In capture mode: Capture / Skip / Skip the rest.
;   5. Size menu: 12pt only / 6pt to 24pt / All sizes.
;   6. For each chosen font, each available chosen size, and EVERY style
;      the list entry reports (bit 0 Normal, 1 Bold, 2 Italic, 3 Bold
;      Italic): every single code 01-FF, then every accent D0-DF over every
;      base ROSAN283 allows accents on (space, A-Z, a-z, 91-94, 9B, 9D).
;      Codes the font does not define (charinfo A=5) get a header only.
;
; FILES: F + font ID (4 hex digits) + style letter (N, B, I, J = bold
;   italic) + size (2 digits) + .FD6, e.g. F0100B12.FD6 = ID #0100 Bold
;   12pt. A file that already exists is SKIPPED, never overwritten, so an
;   interrupted run is resumed by starting FONTCAP again (delete the
;   incomplete file first: the converter reports files without END).
;
; CAPTURE: as FONTDMP5 (src/fontdmp5.asm, XAnne run 6), whose per-glyph
; code (do_glyph, gl_draw, cap_rect) and file/list/alert helpers are used
; unchanged: W render (white ground) for the ink, K render (black ground)
; for the raster box, both read with bios_getpxl; rect from Rosanne's own
; metrics at 22 units/px with margins 3 + size/8 px across (+ size/4 more
; for italic styles, which lean) and 2 + size/4 rows above and below.
; Limits: 20 bytes x 144 rows, at most 136 rows above and 56 below the
; baseline (the drawing area); a clamped rect is flagged in the glyph
; record and the converter reports any glyph touching its rect edge.
;
; VERIFIED vs NOT: verified in XAnne (run 7, docs/AUDIT.md) for Times
; (#0100, Normal + Bold) and Swiss (#0101, Normal) at all ten sizes: the
; list walk, size probe, FONTLIST.TXT, alerts, resume and the captures,
; which rebuild fonts identical to FONTDMP4/5's. Not yet verified: other
; typefaces, more than two list entries, Italic / Bold Italic styles.
;
; SAFETY as FONTDMP4/5: one empty slot used and cleared; the original slot,
; clip window, ink and mode restored; pointer hidden while drawing; drawing
; confined to the drawing area (clip window set to it); font files are
; only used through the OS.
;
; Build: build.sh (pasmo --bin src/fontcap.asm build/FONTCAP.PRG).
; ============================================================================

OS              equ 003Bh
B_GETMEM0       equ 0C8h
B_GETMEM1       equ 0CBh
B_GETMEM2       equ 0CEh
B_GETMEM3       equ 0D1h
B_SETMEM2       equ 0C2h
B_GETTIME       equ 0B0h        ; BIOS #10: E ticks, D s, C min, B h
B_SETINK        equ 0E0h
B_GETINK        equ 0E3h
B_SETMODE       equ 0E6h
B_GETMODE       equ 0E9h
B_GETPXL        equ 0F5h

F_APP_EXIT      equ 23
F_COPY24        equ 41
F_ALERT         equ 76
F_TYPO_INIT     equ 83
F_TYPO_GETLIST  equ 84
F_TYPO_SELECT   equ 85
F_TYPO_GETSEL   equ 86
F_TYPO_DEF      equ 87
F_TYPO_CLR      equ 88
F_TYPO_INFO     equ 90
F_TYPO_CHARINFO equ 92
F_TYPO_CHARSCR  equ 93
F_MOUSE_OFF     equ 111
F_MOUSE_ON      equ 112
F_SCR_DIRECT    equ 117
F_SCR_WINDOW    equ 118
F_SCR_GETWINDOW equ 119
F_OPEN          equ 144
F_CLOSE         equ 145
F_WRITE         equ 146

DG_WHITE        equ 1
DG_BLACK        equ 2

; drawing area (clip window) and glyph origin
AX              equ 112
AY              equ 64
AW              equ 288
AH              equ 192
GX              equ 160
GY              equ 200
MAX_ASC         equ GY-AY       ; rect rows above the baseline (136)
MAX_DESC        equ AY+AH-GY    ; rect rows below it (56)
MARGIN_X        equ 3           ; base margins; + size/8 across, size/4 rows
MARGIN_Y        equ 2
SAFE_UPP        equ 22          ; units per pixel used to size rects
MAX_ROWB        equ 20
MAX_H           equ 144
BUFN            equ MAX_ROWB*MAX_H
ACC_FIRST       equ 0D0h
ACC_LAST        equ 0DFh

MAX_FONTS       equ 20
FONT_REC        equ 37
LDATA           equ MAX_FONTS*FONT_REC
L_COPY          equ 8
L_MAP           equ 8+LDATA
LREC            equ 8+2*LDATA
GH_LEN          equ 28          ; GLY4 header

LOW_NAME        equ 2100h
LOW_EXT         equ 2120h
LOW_DG          equ 2200h
LOW_WIN         equ 2220h

    org 4000h
    defs 100h

; ============================================================================
start:
    call B_GETMEM1
    ld (app_bank),a
    ld hl,lst1
    call list_read              ; first OS call, as FONTDMP2-5
    call B_GETINK
    ld (env_ink),a
    call B_GETMODE
    ld (env_mode),a
    ld a,F_TYPO_GETSEL
    call OS
    ld a,e
    ld (env_slot),a
    ld a,F_SCR_GETWINDOW
    call OS
    ld de,env_win
    ld ix,8
    call fd_copy24
    push af
    pop hl
    ld a,l
    ld (env_win_f),a

    ; ---- menu --------------------------------------------------------------
    ld hl,menu_def
    ld de,menu_len
    ld a,(app_bank)
    ld c,a
    ld a,F_ALERT
    call OS
    jp c,exit                   ; refused: nothing touched
    cp 2
    jp nc,exit                  ; Cancel (or Stop)
    ld (run_mode),a             ; 0 = capture, 1 = list only

    ; ---- slot survey (as FONTDMP4/5) ---------------------------------------
    xor a
    ld (sv_e),a
slot_survey:
    ld a,(sv_e)
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    ld c,a
    ld a,(sv_e)
    ld e,a
    ld d,0
    ld hl,slot_tab
    add hl,de
    ld (hl),c
    inc a
    ld (sv_e),a
    cp 16
    jp nz,slot_survey
    ld hl,slot_tab+1
    ld b,15
    ld c,1
slot_pick:
    ld a,(hl)
    cp 4
    jp z,slot_found
    inc hl
    inc c
    djnz slot_pick
    ld a,(slot_tab)
    cp 4
    jp nz,no_slot
    ld c,0
slot_found:
    ld a,c
    ld (slot_use),a
    ld hl,slot_tab
    ld b,16
    ld a,1
    ld (all_empty),a
slot_empty_chk:
    ld a,(hl)
    cp 4
    jp z,slot_empty_next
    xor a
    ld (all_empty),a
slot_empty_next:
    inc hl
    djnz slot_empty_chk

    ; ---- font list, test definition, guarded init (as FONTDMP4/5) ----------
    ld hl,lst1
    ld (lst_cur),hl
    call pick_source
    call test_def
    jp z,fonts_ok
    ld a,(all_empty)
    or a
    jp z,fonts_ok               ; cannot init safely: fonts will fail
    ld a,F_TYPO_INIT
    call OS
    push af
    pop hl
    ld a,l
    ld (init_f),a
    ld a,1
    ld (init_done),a
    ld hl,lst2
    call list_read
    ld hl,lst2
    ld (lst_cur),hl
    call pick_source
    call test_def
fonts_ok:

    ; ---- discovery: probe sizes, FONTLIST.TXT, one alert per font ----------
    call probe_all
    call write_list
    call ask_fonts
    ld a,(run_mode)
    or a
    jp nz,finish_list
    ld a,(n_chosen)
    or a
    jp z,finish_list
    ld hl,size_menu
    ld de,size_menu_len
    ld a,(app_bank)
    ld c,a
    ld a,F_ALERT
    call OS
    jp c,finish_list            ; refused: nothing captured
    cp 3
    jp nc,finish_list
    ld (size_mode),a            ; 0 = 12pt, 1 = 6-24pt, 2 = all

    ; ==== the drawing area ===================================================
    ld a,F_MOUSE_OFF
    call OS
    xor a
    call B_SETINK
    xor a
    call B_SETMODE
    ld hl,area_rect
    call fd_window
    ld hl,area_rect
    ld a,DG_WHITE
    call fd_dg

    ; ==== sizes x chosen fonts x listed styles ===============================
    xor a
    ld (v_pk),a
cap_size:
    ld a,(v_pk)
    ld e,a
    ld d,0
    ld hl,size_asc
    add hl,de
    ld a,(hl)
    or a
    jp z,all_done
    ld (cur_size),a
    call size_wanted
    jp nz,cap_next_size
    xor a
    ld (v_pi),a
cap_font:
    ld a,(v_pi)
    ld hl,lst_n
    cp (hl)
    jp nc,cap_next_size
    ld hl,f_chosen
    call arr_pi
    ld a,(hl)
    or a
    jp z,cap_next_font
    ld a,(v_pi)
    call font_mask
    ld a,(v_pk)
    call mask_test
    jp nz,cap_has
    ld hl,n_missing             ; chosen font lacks this size
    inc (hl)
    jp cap_next_font
cap_has:
    ld a,(v_pi)
    call entry_ptr
    ld (cf_entry),hl
    inc hl
    inc hl
    ld a,(hl)
    ld (cf_listed),a            ; styles as listed
    xor a
    ld (cur_style),a
cap_style:
    ld a,(cur_style)
    ld b,a
    inc b
    ld a,(cf_listed)
cs_shift:
    dec b
    jp z,cs_test
    rrca
    jp cs_shift
cs_test:
    and 1
    jp z,cap_next_style
    ld a,(cur_style)
    ld (cf_style),a
    call do_combo
cap_next_style:
    ld a,(cur_style)
    inc a
    ld (cur_style),a
    cp 4
    jp nz,cap_style
cap_next_font:
    ld hl,v_pi
    inc (hl)
    jp cap_font
cap_next_size:
    ld hl,v_pk
    inc (hl)
    jp cap_size
all_done:
    call fd_window_restore
    ld a,(env_mode)
    call B_SETMODE
    ld a,(env_ink)
    call B_SETINK
    ld a,F_MOUSE_ON
    call OS
finish_list:
    ld a,(env_slot)
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    call show_summary
exit:
    ld a,F_APP_EXIT
    call OS
    ret

no_slot:
    ld a,(env_slot)
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    ld de,al_text
    ld hl,t_noslot
    call al_puts
    call al_show
    jp exit

; size_wanted -- Z if cur_size is in the chosen size set
size_wanted:
    ld a,(size_mode)
    or a
    jp nz,sw_range
    ld a,(cur_size)
    cp 12
    ret
sw_range:
    cp 1
    jp nz,sw_yes
    ld a,(cur_size)
    cp 25
    jp nc,sw_no
sw_yes:
    xor a
    ret
sw_no:
    or 1
    ret

; ============================================================================
; one font, one style, one size
; ============================================================================
do_combo:
    ; stem: F + ID (4 hex) + style letter + size (2 digits)
    ld de,stem
    ld a,'F'
    ld (de),a
    inc de
    ld hl,(cf_entry)
    inc hl
    ld a,(hl)                   ; ID high byte
    call al_hex
    dec hl
    ld a,(hl)                   ; ID low byte
    call al_hex
    ld a,(cf_style)
    ld l,a
    ld h,0
    ld bc,style_ch
    add hl,bc
    ld a,(hl)
    ld (de),a
    inc de
    ld a,(cur_size)
    ld c,'0'-1
dc_t:
    inc c
    sub 10
    jp nc,dc_t
    add a,10+'0'
    ld b,a
    ld a,c
    ld (de),a
    inc de
    ld a,b
    ld (de),a
    inc de
    xor a
    ld (de),a
    ; styles for os_typo_def: as listed, bit 0 forced (ROSAN283)
    ld a,(cf_listed)
    or 1
    ld (cf_styles),a
    ; skip if the file exists
    ld hl,ext_fd6
    call fd_exists
    jp nz,dc_skip
    ; define
    ld a,(slot_use)
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    ld hl,(cf_entry)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld a,(cf_styles)
    ld d,a
    ld a,(cur_size)
    ld b,a
    ld a,F_TYPO_DEF
    call OS
    ld (cf_def_a),a
    push af
    pop hl
    ld a,l
    ld (cf_def_f),a
    ld a,(cf_def_a)
    or a
    jp nz,dc_fail_def
    ; margins for this size: 3 + size/8 px across (+ size/4 for italic),
    ; 2 + size/4 rows above and below
    ld a,(cur_size)
    srl a
    srl a
    ld b,a                      ; size/4
    add a,MARGIN_Y
    ld (cf_my),a
    ld a,b
    srl a
    add a,MARGIN_X
    ld c,a
    ld a,(cf_style)
    and 2
    ld a,c
    jp z,dc_mx
    add a,b
dc_mx:
    ld (cf_mx),a
    ; metrics for the rect height
    xor a
    ld (rect_flags),a
    ld a,F_TYPO_INFO
    call OS
    ld (info_a),a
    ld (info_hl),hl
    or a
    jp nz,dc_noinfo
    ld a,h
    cp 40h
    jp nc,dc_noinfo
    ld de,info_data
    ld bc,8
    ldir
dc_noinfo:
    ld hl,(info_data+2)         ; max ascender
    call div22c
    ld hl,cf_my
    add a,(hl)
    cp MAX_ASC+1
    jp c,dc_asc_ok
    ld a,(rect_flags)
    or 4
    ld (rect_flags),a
    ld a,MAX_ASC
dc_asc_ok:
    ld (rect_asc),a
    ld hl,(info_data+4)         ; max descender
    call div22c
    ld hl,cf_my
    add a,(hl)
    cp MAX_DESC+1
    jp c,dc_desc_ok
    ld a,(rect_flags)
    or 8
    ld (rect_flags),a
    ld a,MAX_DESC
dc_desc_ok:
    ld b,a
    ld a,(rect_asc)
    add a,b
    ld (rect_h),a
    cp MAX_H+1
    jp c,dc_h_ok
    ld a,MAX_H
    ld (rect_h),a
    ld a,(rect_flags)
    or 1
    ld (rect_flags),a
dc_h_ok:
    ld a,(rect_asc)
    ld e,a
    ld d,0
    ld hl,GY
    or a
    sbc hl,de
    ld (cr_y),hl
    ; file
    ld hl,ext_fd6
    call fd_open
    jp c,dc_fail_open
    ld hl,hdr_fd6
    ld de,8
    call fd_raw
    ld a,6
    ld (hdr_var),a              ; version
    ld a,4
    ld (hdr_var+1),a            ; stage
    ld a,(v_pi)
    ld (hdr_var+2),a            ; list position
    ld a,(cur_size)
    ld (hdr_var+3),a
    ld hl,(cf_entry)
    ld a,(hl)
    ld (hdr_var+4),a
    inc hl
    ld a,(hl)
    ld (hdr_var+5),a
    ld a,(cf_styles)
    ld (hdr_var+6),a
    ld a,(cf_style)
    ld (hdr_var+7),a
    ld hl,hdr_var
    ld de,8
    call fd_raw
    ; FACE: list entry, def A/F, init flags
    ld hl,(cf_entry)
    ld de,face_rec
    ld bc,FONT_REC
    ldir
    ld a,(cf_def_a)
    ld (face_rec+37),a
    ld a,(cf_def_f)
    ld (face_rec+38),a
    ld a,(init_done)
    ld (face_rec+39),a
    ld a,(init_f)
    ld (face_rec+40),a
    ld a,(slot_use)
    ld (face_rec+41),a
    ld a,(lst_src)
    ld (face_rec+42),a
    ld hl,tag_face
    ld de,43
    ld bc,face_rec
    call fd_record
    ld hl,tag_info
    ld de,11
    ld bc,info_a
    call fd_record
    call B_GETTIME
    ld (tim_buf),de
    ld (tim_buf+2),bc
    ld hl,tag_tim0
    ld de,4
    ld bc,tim_buf
    call fd_record
    ; characters: pass 1 every single code 01-FF, pass 2 accent x base
    ld hl,0
    ld (cf_glyphs),hl
    xor a
    ld (cur_acc),a
    ld a,1
    ld (cur_ch),a
sg_loop:
    call do_glyph
    ld a,(cur_ch)
    inc a
    ld (cur_ch),a
    jp nz,sg_loop
    ld a,ACC_FIRST
    ld (cur_acc),a
ac_loop:
    ld hl,base_tab
    ld (ct_ptr),hl
ab_loop:
    ld hl,(ct_ptr)
    ld a,(hl)
    or a
    jp z,ab_done
    inc hl
    ld (ct_ptr),hl
    ld (cur_ch),a
    call do_glyph
    jp ab_loop
ab_done:
    ld a,(cur_acc)
    cp ACC_LAST
    jp z,ch_done
    inc a
    ld (cur_acc),a
    jp ac_loop
ch_done:
    call B_GETTIME
    ld (tim_buf),de
    ld (tim_buf+2),bc
    ld hl,tag_tim1
    ld de,4
    ld bc,tim_buf
    call fd_record
    ld hl,tag_end
    ld de,0
    ld bc,0
    call fd_record
    call fd_close
    ; release the slot
    ld a,(slot_use)
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    ld a,F_TYPO_CLR
    call OS
    ld a,(wr_err)
    or a
    jp nz,dc_fail_write
    ld hl,n_done
    inc (hl)
    ld hl,stem
    ld de,last_done
    ld bc,9
    ldir
    ret
dc_skip:
    ld hl,n_skip
    inc (hl)
    ret
dc_fail_def:
    ld a,(cf_def_a)
    ld (fail_code),a
    ld a,'D'
    jp dc_fail
dc_fail_open:
    ld a,(slot_use)             ; release the slot defined above
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    ld a,F_TYPO_CLR
    call OS
    ld a,(wr_err)
    ld (fail_code),a
    ld a,'O'
    jp dc_fail
dc_fail_write:
    ld a,(wr_err)
    ld (fail_code),a
    ld a,'W'
dc_fail:
    ld (fail_kind),a
    ld hl,n_fail
    inc (hl)
    ld hl,stem
    ld de,last_fail
    ld bc,9
    ldir
    ret

; ============================================================================
; one glyph: charinfo, W and K renders, GLY4 record
; ============================================================================
do_glyph:
    ld hl,gh
    ld b,GH_LEN
dg_clear:
    ld (hl),0
    inc hl
    djnz dg_clear
    ld a,(cur_ch)
    ld (gh+0),a
    ld a,(cur_acc)
    ld (gh+1),a
    ld a,(cf_style)
    ld (gh+2),a
    ld a,0FFh
    ld (gh+11),a
    ld (gh+12),a
    ld hl,GX
    ld (gh+14),hl
    ld hl,GY
    ld (gh+16),hl
    ; os_typo_charinfo (D = style: bit 0 bold)
    ld a,(cur_acc)
    ld b,a                      ; accent (0 = none)
    ld a,(cur_ch)
    ld c,a
    ld a,(cf_style)
    and 1                       ; ROSAN283: only bit 0 (Bold) of D is obeyed
    ld d,a
    ld a,F_TYPO_CHARINFO
    call OS
    ld (gh+5),de
    ld (gh+7),hl
    ld (gh+9),bc
    push af
    pop hl
    ld a,h
    ld (gh+3),a
    ld a,l
    ld (gh+4),a
    ld a,h
    or a
    jp nz,gl_header_only        ; undefined character: metrics only
    ; rect: x from GX-3, width ceil(w/22)+6 rounded up to bytes
    ld hl,(gh+5)
    call div22c
    ld hl,cf_mx                 ; width ceil(w/22) + 2 margins, rounded up to bytes
    add a,(hl)
    add a,(hl)
    add a,7
    srl a
    srl a
    srl a                       ; bytes per row
    cp MAX_ROWB+1
    jp c,gl_rowb_ok
    ld a,(rect_flags)
    or 2
    ld (rect_flags),a
    ld a,MAX_ROWB
gl_rowb_ok:
    ld (cr_rowb),a
    ld (gh+26),a
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    ld (gh+22),hl               ; rect width in pixels
    ld a,(cf_mx)
    ld e,a
    ld d,0
    ld hl,GX
    or a
    sbc hl,de
    ld (cr_x),hl
    ld (gh+18),hl
    ld hl,(cr_y)
    ld (gh+20),hl
    ld a,(rect_h)
    ld (cr_h),a
    ld l,a
    ld h,0
    ld (gh+24),hl
    ld a,(rect_flags)
    ld (gh+13),a
    ; capture size = rowb * h
    ld a,(cr_rowb)
    ld e,a
    ld d,0
    ld hl,0
    ld a,(rect_h)
    ld b,a
gl_mul:
    add hl,de
    djnz gl_mul
    ld (cap_len),hl
    ; dg rect = x, y, w, h
    ld hl,(gh+18)
    ld (dg_rect),hl
    ld hl,(gh+20)
    ld (dg_rect+2),hl
    ld hl,(gh+22)
    ld (dg_rect+4),hl
    ld hl,(gh+24)
    ld (dg_rect+6),hl
    ; W render
    ld hl,dg_rect
    ld a,DG_WHITE
    call fd_dg
    call gl_draw
    ld (gh+11),a
    ld hl,buf_w
    call cap_rect
    ; K render
    ld hl,dg_rect
    ld a,DG_BLACK
    call fd_dg
    call gl_draw
    ld (gh+12),a
    ld hl,buf_k
    call cap_rect
    ; record: tag, length = header + 2 captures
    ld hl,(cap_len)
    add hl,hl
    ld de,GH_LEN
    add hl,de
    ld (rec_hdr+4),hl
    call gl_tag
    ld hl,gh
    ld de,GH_LEN
    call fd_raw
    ld hl,buf_w
    ld de,(cap_len)
    call fd_raw
    ld hl,buf_k
    ld de,(cap_len)
    call fd_raw
    jp gl_counted
gl_header_only:
    ld hl,GH_LEN
    ld (rec_hdr+4),hl
    call gl_tag
    ld hl,gh
    ld de,GH_LEN
    call fd_raw
gl_counted:
    ld hl,(cf_glyphs)
    inc hl
    ld (cf_glyphs),hl
    ret

gl_tag:
    ld hl,tag_gly4
    ld de,rec_hdr
    ld bc,4
    ldir
    ld hl,rec_hdr
    ld de,6
    jp fd_raw

; gl_draw -- os_typo_charscreen of cur_ch with accent cur_acc at (GX,GY),
; opaque, cf_style.
; out: A = result
gl_draw:
    ld a,(cf_style)
    ld l,a
    ld h,0                      ; IX hi = mode 0 opaque
    push hl
    pop ix
    ld a,(cur_acc)
    ld b,a                      ; accent (0 = none)
    ld a,(cur_ch)
    ld c,a
    ld de,GX
    ld hl,GY
    ld a,F_TYPO_CHARSCR
    call OS
    ret

; cap_rect -- bios_getpxl capture of cr_x, cr_y, cr_rowb bytes x cr_h rows
; into HL: row-major, bit 7 leftmost, 1 = white.
cap_rect:
    ld (cp_dst),hl
    xor a
    ld (cp_y),a
cr_row:
    ld hl,(cr_x)
    ld (cp_px),hl
    ld a,(cr_rowb)
    ld (cp_nb),a
cr_byte:
    ld c,0
    ld b,8
cr_bit:
    push bc
    ld de,(cp_px)
    ld a,(cp_y)
    ld l,a
    ld h,0
    ld bc,(cr_y)
    add hl,bc
    call B_GETPXL
    pop bc
    and 1
    sla c
    or c
    ld c,a
    ld hl,(cp_px)
    inc hl
    ld (cp_px),hl
    djnz cr_bit
    ld hl,(cp_dst)
    ld (hl),c
    inc hl
    ld (cp_dst),hl
    ld a,(cp_nb)
    dec a
    ld (cp_nb),a
    jp nz,cr_byte
    ld a,(cp_y)
    inc a
    ld (cp_y),a
    ld hl,cr_h
    cp (hl)
    jp nz,cr_row
    ret

; div22c -- A = ceil(HL / SAFE_UPP) (HL <= 5600)
div22c:
    ld c,0
d22_loop:
    ld a,h
    or l
    jp z,d22_done
    inc c
    ld de,SAFE_UPP
    or a
    sbc hl,de
    jp nc,d22_loop
d22_done:
    ld a,c
    ret



; ============================================================================
; fonts: list source, test definition, size probe, FONTLIST.TXT, choice
; ============================================================================
; pick_source -- lst_ents / lst_n from the list block at lst_cur: the
; os_copy_24bit copy if any entry in it is valid, else the mapped read if
; that is, else none (lst_n = 0). lst_src = 'C', 'M' or 0.
pick_source:
    xor a
    ld (lst_src),a
    ld (lst_n),a
    ld hl,(lst_cur)
    ld de,5
    add hl,de
    ld a,(hl)                   ; n (at most MAX_FONTS)
    or a
    ret z
    ld b,a
    ld hl,(lst_cur)
    ld de,L_COPY
    add hl,de
    push bc
    call any_valid
    pop bc
    ld a,'C'
    jp z,ps_set
    ld hl,(lst_cur)
    ld de,7
    add hl,de
    ld a,(hl)                   ; map status: 1 = read
    cp 1
    ret nz
    ld hl,(lst_cur)
    ld de,L_MAP
    add hl,de
    push bc
    call any_valid
    pop bc
    ret nz
    ld a,'M'
ps_set:
    ld (lst_src),a
    ld (lst_ents),hl
    ld a,b
    ld (lst_n),a
    ret

; any_valid -- HL = first entry, B = count: Z if any entry is valid.
; HL preserved.
any_valid:
    push hl
av_loop:
    call pf_valid
    jp z,av_yes
    ld de,FONT_REC
    add hl,de
    djnz av_loop
    pop hl
    or 1
    ret
av_yes:
    pop hl
    xor a
    ret

; first_valid -- HL = the first valid entry, else the fallback entry
; (ID #0100, XAnne runs 1/2)
first_valid:
    ld a,(lst_n)
    or a
    jp z,fv_none
    ld b,a
    ld hl,(lst_ents)
fv_loop:
    call pf_valid
    ret z
    ld de,FONT_REC
    add hl,de
    djnz fv_loop
fv_none:
    ld hl,fb_entry
    ret

; test_def -- define the first valid entry at 12pt in slot_use and clear it.
; out: Z if the typo system answered: A=0, or A=2 (the font exists but has
; no 12pt). Any other result (1 = font does not exist: the system is not
; initialised, XAnne run 2) gives NZ.
test_def:
    call first_valid
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld a,(hl)
    or 1
    push de
    push af
    ld a,(slot_use)
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    pop af
    ld d,a
    pop hl
    ld b,12
    ld a,F_TYPO_DEF
    call OS
    ld (test_a),a
    or a
    jp nz,td_out
    ld a,F_TYPO_CLR
    call OS
td_out:
    ld a,(test_a)
    or a
    ret z
    cp 2
    ret

; entry_ptr -- A = list position: HL = its entry. B, DE corrupt.
entry_ptr:
    ld hl,(lst_ents)
    or a
    ret z
    ld b,a
    ld de,FONT_REC
ep_loop:
    add hl,de
    djnz ep_loop
    ret

; arr_pi -- HL = HL + (v_pi). A, DE corrupt.
arr_pi:
    ld a,(v_pi)
    ld e,a
    ld d,0
    add hl,de
    ret

; font_mask -- A = list position: HL = its size mask. DE preserved.
font_mask:
    ld l,a
    ld h,0
    add hl,hl
    push de
    ld de,f_mask
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    pop de
    ret

; mask_test -- HL = mask, A = bit: NZ if set. B, HL corrupt.
mask_test:
    or a
    jp z,mt_test
    ld b,a
mt_shift:
    srl h
    rr l
    djnz mt_shift
mt_test:
    ld a,l
    and 1
    ret

; probe_all -- for every list entry: f_valid (pf_valid), and for valid ones
; os_typo_def at every size in size_asc in slot_use, cleared at once.
; f_mask bit k = size k defined; f_err = the first result other than 0 and
; 2 (size out of range). n_fonts = valid entries.
probe_all:
    xor a
    ld (n_fonts),a
    ld (v_pi),a
pa_font:
    ld a,(v_pi)
    ld hl,lst_n
    cp (hl)
    ret nc
    call entry_ptr
    ld (v_pe),hl
    ld hl,0
    ld (pmask),hl
    xor a
    ld (perr),a
    ld (v_pv),a
    ld hl,(v_pe)
    call pf_valid
    jp nz,pa_store
    ld a,1
    ld (v_pv),a
    ld hl,n_fonts
    inc (hl)
    xor a
    ld (v_pk),a
pa_size:
    ld a,(v_pk)
    ld e,a
    ld d,0
    ld hl,size_asc
    add hl,de
    ld a,(hl)
    or a
    jp z,pa_store
    ld (psz),a
    ld a,(slot_use)
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    ld hl,(v_pe)
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld a,(hl)
    or 1
    ex de,hl                    ; HL = ID
    ld d,a                      ; D = styles
    ld a,(psz)
    ld b,a
    ld a,F_TYPO_DEF
    call OS
    or a
    jp nz,pa_nodef
    ld a,F_TYPO_CLR
    call OS
    ld hl,1
    ld a,(v_pk)
    or a
    jp z,pa_bit
    ld b,a
pa_shift:
    add hl,hl
    djnz pa_shift
pa_bit:
    ld de,(pmask)
    ld a,l
    or e
    ld l,a
    ld a,h
    or d
    ld h,a
    ld (pmask),hl
    jp pa_next_size
pa_nodef:
    cp 2
    jp z,pa_next_size
    ld b,a
    ld a,(perr)
    or a
    jp nz,pa_next_size
    ld a,b
    ld (perr),a
pa_next_size:
    ld hl,v_pk
    inc (hl)
    jp pa_size
pa_store:
    ld a,(v_pi)
    ld l,a
    ld h,0
    add hl,hl
    ld de,f_mask
    add hl,de
    ld de,(pmask)
    ld (hl),e
    inc hl
    ld (hl),d
    ld hl,f_err
    call arr_pi
    ld a,(perr)
    ld (hl),a
    ld hl,f_valid
    call arr_pi
    ld a,(v_pv)
    ld (hl),a
    ld hl,v_pi
    inc (hl)
    jp pa_font

; desc_a -- A = list position: "Font n of N: <name>  ID=xxxx RTF=f" at DE
desc_a:
    ld (dpos),a
    ld hl,t_font
    call al_puts
    ld a,(dpos)
    inc a
    call al_dec8
    ld hl,t_of
    call al_puts
    ld a,(lst_n)
    call al_dec8
    ld hl,t_colon
    call al_puts
    push de
    ld a,(dpos)
    call entry_ptr
    pop de
    push hl
    ld bc,4
    add hl,bc
    call al_name
    ld hl,t_id
    call al_puts
    pop hl
    push hl
    inc hl
    ld a,(hl)
    call al_hex
    dec hl
    ld a,(hl)
    call al_hex
    ld hl,t_rtf
    call al_puts
    pop hl
    inc hl
    inc hl
    inc hl
    ld a,(hl)
    jp al_dec8

; desc_b -- A = list position: "Styles ss: Normal Bold.  Sizes: 6 8 ..." at DE
desc_b:
    ld (dpos),a
    push de
    call entry_ptr
    pop de
    inc hl
    inc hl
    ld a,(hl)
    ld (dsty),a
    ld hl,t_styles
    call al_puts
    ld a,(dsty)
    call al_hex
    ld a,':'
    ld (de),a
    inc de
    ld a,(dsty)
    and 1
    ld hl,t_nrm
    call nz,al_puts
    ld a,(dsty)
    and 2
    ld hl,t_bold
    call nz,al_puts
    ld a,(dsty)
    and 4
    ld hl,t_ital
    call nz,al_puts
    ld a,(dsty)
    and 8
    ld hl,t_bital
    call nz,al_puts
    ld hl,t_sizes
    call al_puts
    ld a,(dpos)
    call font_mask
    ld a,h
    or l
    jp nz,db_have
    ld hl,t_none
    call al_puts
    jp db_err
db_have:
    xor a
    ld (dk),a
db_loop:
    ld a,(dk)
    ld c,a
    ld b,0
    ld hl,size_asc
    add hl,bc
    ld a,(hl)
    or a
    jp z,db_err
    ld a,(dpos)
    call font_mask
    ld a,(dk)
    call mask_test
    jp z,db_next
    ld a,' '
    ld (de),a
    inc de
    ld a,(dk)
    ld c,a
    ld b,0
    ld hl,size_asc
    add hl,bc
    ld a,(hl)
    call al_dec8
db_next:
    ld hl,dk
    inc (hl)
    jp db_loop
db_err:
    ld a,(dpos)
    ld hl,f_err
    ld c,a
    ld b,0
    add hl,bc
    ld a,(hl)
    or a
    ret z
    ld hl,t_deferr
    call al_puts
    ld a,(dpos)
    ld hl,f_err
    ld c,a
    ld b,0
    add hl,bc
    ld a,(hl)
    call al_hex
    ld a,')'
    ld (de),a
    inc de
    ret

; write_list -- FONTLIST.TXT: one header line, one line per list entry.
; Never overwrites: lst_file = 'W' written, 'E' already exists, 'F' failed.
write_list:
    ld hl,name_list
    ld de,stem
    ld bc,9
    ldir
    ld hl,ext_txt
    call fd_exists
    ld a,'E'
    jp nz,wl_set
    ld hl,ext_txt
    call fd_open
    ld a,'F'
    jp c,wl_set
    ld de,al_text
    ld hl,t_lh1
    call al_puts
    ld hl,(lst_cur)
    ld a,(hl)                   ; getlist B
    call al_dec8
    ld hl,t_lh2
    call al_puts
    ld a,(lst_src)
    or a
    jp nz,wl_src
    ld a,'-'
wl_src:
    ld (de),a
    inc de
    ld hl,t_lh3
    call al_puts
    ld a,(n_fonts)
    call al_dec8
    ld hl,t_lh4
    call al_puts
    ld a,(test_a)
    call al_hex
    ld hl,t_init
    call al_puts
    ld a,(init_f)
    call al_hex
    call wl_out
    xor a
    ld (v_pi),a
wl_loop:
    ld a,(v_pi)
    ld hl,lst_n
    cp (hl)
    jp nc,wl_close
    ld hl,f_valid
    call arr_pi
    ld a,(hl)
    or a
    ld de,al_text
    jp nz,wl_valid
    ld hl,t_font
    call al_puts
    ld a,(v_pi)
    inc a
    call al_dec8
    ld hl,t_invalid
    call al_puts
    jp wl_line
wl_valid:
    ld a,(v_pi)
    call desc_a
    ld hl,t_bar
    call al_puts
    ld a,(v_pi)
    call desc_b
wl_line:
    call wl_out
    ld hl,v_pi
    inc (hl)
    jp wl_loop
wl_close:
    call fd_close
    ld a,(wr_err)
    or a
    ld a,'W'
    jp z,wl_set
    ld a,'F'
wl_set:
    ld (lst_file),a
    ret

; wl_out -- CR LF after the text at al_text..DE, then write it
wl_out:
    ld a,13
    ld (de),a
    inc de
    ld a,10
    ld (de),a
    inc de
    ld hl,al_text
    ex de,hl
    or a
    sbc hl,de
    ex de,hl                    ; DE = length
    ld hl,al_text
    jp fd_raw

; ask_fonts -- one alert per valid font. Capture mode: Capture / Skip /
; Skip the rest (f_chosen, n_chosen); a font with no size gets OK only.
; List mode: OK only.
ask_fonts:
    xor a
    ld (n_chosen),a
    ld hl,f_chosen
    ld b,MAX_FONTS
af_clear:
    ld (hl),a
    inc hl
    djnz af_clear
    ld (v_pi),a
af_loop:
    ld a,(v_pi)
    ld hl,lst_n
    cp (hl)
    ret nc
    ld hl,f_valid
    call arr_pi
    ld a,(hl)
    or a
    jp z,af_next
    ld de,al_text
    ld a,(v_pi)
    call desc_a
    xor a
    ld (de),a                   ; end of line 1
    inc de
    ld a,(v_pi)
    call desc_b
    ld a,(run_mode)
    or a
    jp nz,af_ok
    ld a,(v_pi)
    call font_mask
    ld a,h
    or l
    jp z,af_ok
    ld hl,ask_btns
    ld bc,ask_btns_len
    call al_finish
    ret c                       ; refused: ask no more
    or a
    jp z,af_yes
    cp 1
    jp z,af_next
    ret                         ; Skip the rest
af_yes:
    ld hl,f_chosen
    call arr_pi
    ld (hl),1
    ld hl,n_chosen
    inc (hl)
    jp af_next
af_ok:
    ld hl,ok_btns
    ld bc,ok_btns_len
    call al_finish
af_next:
    ld hl,v_pi
    inc (hl)
    jp af_loop

; al_finish -- end the last text line at DE, append the button block HL
; (BC bytes: count, then keys and label per button) and show the alert.
; out: as os_alert (A = button, carry = refused)
al_finish:
    xor a
    ld (de),a
    inc de
    ld (de),a
    inc de
    ldir
    ld hl,al_text
    ex de,hl
    or a
    sbc hl,de
    ex de,hl                    ; DE = total length
    ld hl,al_text
    ld a,(app_bank)
    ld c,a
    ld a,F_ALERT
    call OS
    ret

; al_name -- the list name at HL (at most 32 characters, NUL-terminated)
; to DE; characters outside 20-7E shown as '?'
al_name:
    ld b,32
an_loop:
    ld a,(hl)
    or a
    ret z
    cp 20h
    jp c,an_q
    cp 7Fh
    jp c,an_put
an_q:
    ld a,'?'
an_put:
    ld (de),a
    inc de
    inc hl
    djnz an_loop
    ret

; al_dec8 -- A as decimal, no leading zeros, at DE. BC, HL corrupt.
al_dec8:
    ld c,0
    ld b,100
    call ad8_digit
    ld b,10
    call ad8_digit
    add a,'0'
    ld (de),a
    inc de
    ret
ad8_digit:
    ld l,0
ad8_loop:
    cp b
    jp c,ad8_done
    sub b
    inc l
    jp ad8_loop
ad8_done:
    ld h,a
    ld a,l
    or c
    jp z,ad8_skip
    ld a,l
    add a,'0'
    ld (de),a
    inc de
    ld c,1
ad8_skip:
    ld a,h
    ret

; ============================================================================
; summary
; ============================================================================
show_summary:
    ld de,al_text
    ld hl,t_sum0
    call al_puts
    ld a,(n_fonts)
    call al_hex
    ld hl,t_chosen
    call al_puts
    ld a,(n_chosen)
    call al_hex
    ld hl,t_sum1
    call al_puts
    ld a,(n_done)
    call al_hex
    ld hl,t_skip
    call al_puts
    ld a,(n_skip)
    call al_hex
    ld hl,t_fail
    call al_puts
    ld a,(n_fail)
    call al_hex
    ld hl,t_miss
    call al_puts
    ld a,(n_missing)
    call al_hex
    call al_show
    ld de,al_text
    ld hl,t_sum2
    call al_puts
    ld a,(test_a)
    call al_hex
    ld hl,t_init
    call al_puts
    ld a,(init_f)
    call al_hex
    ld hl,t_src
    call al_puts
    ld a,(lst_src)
    or a
    jp nz,ss_src
    ld a,'-'
ss_src:
    ld (de),a
    inc de
    ld hl,t_lfile
    call al_puts
    ld a,(lst_file)
    ld (de),a
    inc de
    ld hl,t_last
    call al_puts
    ld hl,last_done
    call al_puts
    call al_show
    ld a,(n_fail)
    or a
    ret z
    ld de,al_text
    ld hl,t_lastfail
    call al_puts
    ld hl,last_fail
    call al_puts
    ld a,' '
    ld (de),a
    inc de
    ld a,(fail_kind)
    ld (de),a
    inc de
    ld a,'='
    ld (de),a
    inc de
    ld a,(fail_code)
    call al_hex
    jp al_show


; ============================================================================
; helpers shared with FONTDMP4/5 (src/fontdmp5.asm), unchanged
; ============================================================================
; fd_exists -- HL = extension text (".FD1",0). out: NZ if FONTDUMP<ext>
; exists (or the probe failed for another reason: safer to refuse), Z if
; os_open_file reported #02 File Not Found.
fd_exists:
    call fd_names
    ld hl,LOW_NAME
    ld de,LOW_EXT
    ld b,0                      ; read mode
    ld a,F_OPEN
    call OS
    jp c,fd_exists_err
    ld b,0
    ld a,F_CLOSE
    call OS
    or 1                        ; NZ: exists
    ret
fd_exists_err:
    cp 2
    ret                         ; Z only for #02

; fd_names -- copy "FONTDUMP",0 to LOW_NAME and the extension at HL to LOW_EXT
fd_names:
    push hl
    ld hl,stem
    ld de,LOW_NAME
    ld bc,9
    ldir
    pop hl
    ld de,LOW_EXT
    ld bc,5
    ldir
    ret

; fd_open -- open FONTDUMP<ext at HL> for write. out: carry = failed
; (wr_err = #80 | ... no: wr_err = OS code, nonzero)
fd_open:
    xor a
    ld (wr_err),a
    call fd_names
    ld hl,LOW_NAME
    ld de,LOW_EXT
    ld b,1
    ld a,F_OPEN
    call OS
    ret nc
    or a
    jp nz,fd_open_code
    ld a,0FFh
fd_open_code:
    ld (wr_err),a
    scf
    ret

; fd_close -- close the write file; a close error is kept unless one is set
fd_close:
    ld b,1
    ld a,F_CLOSE
    call OS
    ret nc
    ld c,a
    ld a,(wr_err)
    or a
    ret nz
    ld a,c
    or a
    jp nz,fd_close_code
    ld a,0FEh
fd_close_code:
    ld (wr_err),a
    ret

; fd_raw -- os_write_file DE bytes from app-bank HL (skipped after an error)
fd_raw:
    ld a,(wr_err)
    or a
    ret nz
    ld a,d
    or e
    ret z
    ld a,(app_bank)
    ld c,a
    ld b,0
    ld a,F_WRITE
    call OS
    ret nc
    or a
    jp nz,fd_raw_code
    ld a,0FDh
fd_raw_code:
    ld (wr_err),a
    ret

; fd_record -- tag at HL (4 bytes), payload length DE, payload address BC
fd_record:
    ld (rec_len),de
    ld (rec_ptr),bc
    ld de,rec_hdr
    ld bc,4
    ldir
    ld hl,(rec_len)
    ld (rec_hdr+4),hl
    ld hl,rec_hdr
    ld de,6
    call fd_raw
    ld hl,(rec_ptr)
    ld de,(rec_len)
    jp fd_raw

; fd_copy24 -- os_copy_24bit IX bytes from C:HL to app-bank DE; F returned
fd_copy24:
    call B_GETMEM1              ; all flags and other registers preserved
    ld b,a
    ld a,F_COPY24
    call OS
    ret

; fd_dg -- os_scr_direct function A on the 8-byte x,y,w,h at HL.
; out: A = F after the call (bit 0 = carry = error, Rosanne 1.12 KI-46)
fd_dg:
    ld (LOW_DG),a
    ld de,LOW_DG+1
    ld bc,8
    ldir
    ld c,80h
    ld hl,LOW_DG
    ld a,F_SCR_DIRECT
    call OS
    push af
    pop hl
    ld a,l
    ret

; fd_window_restore -- put back the window read at start (skipped, A = #FF,
; if that read reported carry)
fd_window_restore:
    ld a,(env_win_f)
    and 1
    ld a,0FFh
    ret nz
    ld hl,env_win
; fd_window -- os_scr_window to the 8-byte x,y,w,h at HL. out: A = F
fd_window:
    ld de,LOW_WIN
    ld bc,8
    ldir
    ld c,80h
    ld hl,LOW_WIN
    ld a,F_SCR_WINDOW
    call OS
    push af
    pop hl
    ld a,l
    ret

; list_read -- os_typo_getlist, then read up to MAX_FONTS entries by
; os_copy_24bit AND by mapping the block at #8000. HL = list-read block.
list_read:
    ld (lr_base),hl
    ld a,F_TYPO_GETLIST
    call OS
    push hl
    ld hl,(lr_base)
    ld (hl),b                   ; +0 count
    inc hl
    ld (hl),c                   ; +1 bank
    inc hl
    pop de
    ld (hl),e                   ; +2 address
    inc hl
    ld (hl),d
    ld a,b
    cp MAX_FONTS+1
    jp c,lr_n_ok
    ld a,MAX_FONTS
lr_n_ok:
    ld hl,(lr_base)
    ld de,5
    add hl,de
    ld (hl),a                   ; +5 n
    or a
    jp nz,lr_have
    inc hl
    inc hl
    ld (hl),3                   ; +7 map status: n = 0
    ret
lr_have:
    ld b,a                      ; lr_len = n * 37
    ld de,FONT_REC
    ld hl,0
lr_mul:
    add hl,de
    djnz lr_mul
    ld (lr_len),hl
    ; (a) os_copy_24bit
    ld hl,(lr_base)
    inc hl
    ld c,(hl)
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    push de
    ld hl,(lr_base)
    ld de,L_COPY
    add hl,de
    ex de,hl                    ; DE = copy destination
    pop hl                      ; HL = source address
    push de
    ld de,(lr_len)
    push de
    pop ix
    pop de
    call fd_copy24
    push af
    pop bc
    ld hl,(lr_base)
    ld de,4
    add hl,de
    ld (hl),c                   ; +4 F
    ; (b) direct read through quarter 2
    call B_GETMEM2
    ld hl,(lr_base)
    ld de,6
    add hl,de
    ld (hl),a                   ; +6 block at #8000 before
    ld hl,(lr_base)
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    and 3Fh
    or 80h
    ld d,a                      ; DE = #8000 + (HL AND #3FFF)
    ld (lr_src),de
    ld hl,(lr_len)
    add hl,de                   ; end address
    ld a,h
    cp 0C0h
    jp c,lr_map_ok
    jp nz,lr_map_skip
    ld a,l
    or a
    jp z,lr_map_ok              ; ends exactly at #C000
lr_map_skip:
    ld hl,(lr_base)
    ld de,7
    add hl,de
    ld (hl),2
    ret
lr_map_ok:
    ld hl,(lr_base)
    inc hl
    ld a,(hl)                   ; the list's block
    call B_SETMEM2
    ld hl,(lr_base)
    ld de,L_MAP
    add hl,de
    ex de,hl
    ld hl,(lr_src)
    ld bc,(lr_len)
    ldir
    ld hl,(lr_base)
    ld de,6
    add hl,de
    ld a,(hl)
    call B_SETMEM2              ; put the original block back
    inc hl
    ld (hl),1                   ; +7 map status: read
    ret

; pf_valid -- Z if the entry at HL looks real: ID <> #FFFF and the first
; name character printable. HL, BC preserved.
pf_valid:
    ld a,(hl)
    inc hl
    and (hl)
    dec hl
    cp 0FFh
    jp z,pf_bad
    push hl
    ld de,4
    add hl,de
    ld a,(hl)
    pop hl
    cp 20h
    jp c,pf_bad
    cp 7Fh
    jp nc,pf_bad
    xor a
    ret
pf_bad:
    or 1
    ret

; al_show -- finish the line at DE as an os_alert definition and show it
; (format as WIDTHDG, XAnne-proven: text NUL, extra NUL, 1 button, keys, "OK")
al_show:
    xor a
    ld (de),a
    inc de
    ld (de),a
    inc de
    ld a,1
    ld (de),a
    inc de
    ld hl,al_keys
    ld bc,11
    ldir
    ld hl,al_text
    ex de,hl
    or a
    sbc hl,de
    ex de,hl                    ; DE = total length
    ld hl,al_text
    ld a,(app_bank)
    ld c,a
    ld a,F_ALERT
    call OS
    ret

; al_puts -- copy NUL-terminated HL to DE (no NUL); DE advanced
al_puts:
    ld a,(hl)
    or a
    ret z
    ld (de),a
    inc hl
    inc de
    jp al_puts

; al_hex -- A as two hex digits at DE
al_hex:
    push af
    rrca
    rrca
    rrca
    rrca
    call al_nib
    pop af
al_nib:
    and 15
    add a,'0'
    cp '9'+1
    jp c,al_nib_out
    add a,7
al_nib_out:
    ld (de),a
    inc de
    ret

; al_dec -- HL as 5 decimal digits at DE
al_dec:
    ld bc,10000
    call al_digit
    ld bc,1000
    call al_digit
    ld bc,100
    call al_digit
    ld bc,10
    call al_digit
    ld bc,1
al_digit:
    ld a,'0'
al_digit_loop:
    or a
    sbc hl,bc
    jp c,al_digit_done
    inc a
    jp al_digit_loop
al_digit_done:
    add hl,bc
    ld (de),a
    inc de
    ret





; ============================================================================
; constant data
; ============================================================================
ext_fd6:    db ".FD6",0
ext_txt:    db ".TXT",0
name_list:  db "FONTLIST",0
hdr_fd6:    db "P16FONT6"
; pass 2: bases accents may go on (ROSAN283 Appendix "Accents"), 0-terminated
base_tab:   db 20h
            db "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            db "abcdefghijklmnopqrstuvwxyz"
            db 91h,92h,93h,94h,9Bh,9Dh
            db 0
tag_face:   db "FACE"
tag_info:   db "INFO"
tag_tim0:   db "TIM0"
tag_tim1:   db "TIM1"
tag_gly4:   db "GLY4"
tag_end:    db "END "
area_rect:  dw AX,AY,AW,AH
; the typo sizes (ROSAN283 os_typo_def), ascending; bit k of f_mask
size_asc:   db 6,8,10,11,12,14,18,24,36,72,0
; file letter per style (charscreen IX lo: bit 0 Bold, bit 1 Italic)
style_ch:   db "NBIJ"
fb_entry:   dw 0100h
            db 1,1
            db "Times? (fallback ID)",0
; menus: os_alert with 3 buttons (keys as the XAnne-proven ASK: first =
; Return/Green, last = Stop/Red)
menu_def:   db "FONTCAP: preserve the typefaces installed on this PcW16.",0
            db "Capture asks which fonts and sizes. List writes FONTLIST.TXT only.",0
            db 0
            db 3
            dw 800Dh,80FBh,0,0
            db "Capture fonts",0
            dw 0,0,0,0
            db "List fonts only",0
            dw 80FEh,80FCh,0,0
            db "Cancel",0
menu_len    equ $-menu_def
size_menu:  db "FONTCAP: which sizes? Existing files are skipped, so a",0
            db "stopped run continues where it left off when started again.",0
            db 0
            db 3
            dw 800Dh,80FBh,0,0
            db "12pt only",0
            dw 0,0,0,0
            db "6pt to 24pt",0
            dw 0,0,0,0
            db "All sizes",0
size_menu_len equ $-size_menu
ask_btns:   db 3
            dw 800Dh,80FBh,0,0
            db "Capture",0
            dw 0,0,0,0
            db "Skip",0
            dw 80FEh,80FCh,0,0
            db "Skip the rest",0
ask_btns_len equ $-ask_btns
ok_btns:    db 1
al_keys:    dw 800Dh,80FBh,0,0
            db "OK",0
ok_btns_len equ $-ok_btns
t_noslot:   db "FONTCAP: no free typo slot (0-15): nothing done",0
t_font:     db "Font ",0
t_of:       db " of ",0
t_colon:    db ": ",0
t_id:       db "  ID=",0
t_rtf:      db " RTF=",0
t_styles:   db "Styles ",0
t_nrm:      db " Normal",0
t_bold:     db " Bold",0
t_ital:     db " Italic",0
t_bital:    db " Bold-Italic",0
t_sizes:    db ".  Sizes:",0
t_none:     db " none",0
t_deferr:   db " (def error ",0
t_bar:      db " | ",0
t_invalid:  db ": invalid list entry",0
t_lh1:      db "FONTCAP font list. getlist entries=",0
t_lh2:      db " source=",0
t_lh3:      db " valid fonts=",0
t_lh4:      db " test def=",0
t_sum0:     db "FONTCAP fonts=",0
t_chosen:   db " chosen=",0
t_sum1:     db " files written=",0
t_skip:     db " skipped(exist)=",0
t_fail:     db " failed=",0
t_miss:     db " no-size=",0
t_sum2:     db "test def=",0
t_init:     db " init=",0
t_src:      db " list=",0
t_lfile:    db " FONTLIST.TXT=",0
t_last:     db " last file=",0
t_lastfail: db "last failure ",0

; ============================================================================
; variables
; ============================================================================
app_bank:   defs 1
wr_err:     defs 1
env_ink:    defs 1
env_mode:   defs 1
env_slot:   defs 1
env_win_f:  defs 1
env_win:    defs 8
run_mode:   defs 1
size_mode:  defs 1
sv_e:       defs 1
slot_tab:   defs 16
slot_use:   db 0FFh
all_empty:  defs 1
init_done:  db 0
init_f:     db 0FFh
test_a:     db 0FFh
lst_cur:    defs 2
lst_src:    defs 1
lst_ents:   defs 2
lst_n:      db 0
lst_file:   db '-'
n_fonts:    db 0
n_chosen:   db 0
v_pi:         defs 1
v_pk:         defs 1
v_pe:         defs 2
v_pv:         defs 1
psz:        defs 1
pmask:      defs 2
perr:       defs 1
dpos:       defs 1
dsty:       defs 1
dk:         defs 1
f_valid:    defs MAX_FONTS
f_chosen:   defs MAX_FONTS
f_err:      defs MAX_FONTS
f_mask:     defs 2*MAX_FONTS
cur_size:   defs 1
cur_style:  defs 1
cur_ch:     defs 1
cur_acc:    defs 1
cf_mx:      defs 1
cf_my:      defs 1
ct_ptr:     defs 2
cf_style:   defs 1
cf_listed:  defs 1
cf_styles:  defs 1
cf_entry:   defs 2
cf_def_a:   defs 1
cf_def_f:   defs 1
cf_glyphs:  defs 2
rect_asc:   defs 1
rect_h:     defs 1
rect_flags: defs 1
cr_x:       defs 2
cr_y:       defs 2
cr_rowb:    defs 1
cr_h:       defs 1
cp_dst:     defs 2
cp_px:      defs 2
cp_y:       defs 1
cp_nb:      defs 1
cap_len:    defs 2
dg_rect:    defs 8
n_done:     db 0
n_skip:     db 0
n_fail:     db 0
n_missing:  db 0
fail_kind:  defs 1
fail_code:  defs 1
stem:       db "F0100N12",0
last_done:  db "(none)",0,0,0
last_fail:  db "(none)",0,0,0
lr_base:    defs 2
lr_len:     defs 2
lr_src:     defs 2
rec_len:    defs 2
rec_ptr:    defs 2
rec_hdr:    defs 6
hdr_var:    defs 8
tim_buf:    defs 4
face_rec:   defs 43
info_a:     db 0FFh             ; INFO record: A, HL, 8 bytes (contiguous)
info_hl:    defs 2
info_data:  defs 8
gh:         defs GH_LEN
al_text:    defs 320
lst1:       defs LREC
lst2:       defs LREC
buf_w:      defs BUFN
buf_k:      defs BUFN
image_end:
