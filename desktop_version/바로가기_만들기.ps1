# ---------------------------------------------------------------------------
# 손글씨 숫자 인식 앱의 바탕 화면 바로가기를 만드는 스크립트입니다.
#
#  - 검은 콘솔 창이 뜨지 않도록 python.exe 대신 pythonw.exe 로 실행합니다.
#  - 바로가기 아이콘을 아이콘.ico 로 지정합니다.
#  - 작업 표시줄 고정이 제대로 동작하도록 바로가기에 앱 식별자(AppUserModelID)를 넣습니다.
#  - 시작 메뉴에도 같은 바로가기를 복사해 검색으로 찾을 수 있게 합니다.
#
# 실행 방법 (PowerShell):
#     powershell -ExecutionPolicy Bypass -File .\바로가기_만들기.ps1
# ---------------------------------------------------------------------------

$프로젝트폴더 = Split-Path -Parent $MyInvocation.MyCommand.Definition
$실행스크립트 = Join-Path $프로젝트폴더 "draw_predict.py"
$아이콘경로   = Join-Path $프로젝트폴더 "아이콘.ico"
$바로가기이름 = "손글씨 숫자 인식기.lnk"
$앱식별자     = "HanyangWomens.MNIST.HandwritingRecognizer.1"   # draw_predict.py 의 값과 반드시 같아야 함

# --- 1) 콘솔 창 없이 실행할 pythonw.exe 찾기 -------------------------------
# 주의: WindowsApps 폴더의 python.exe 는 Microsoft Store 로 연결되는 껍데기라서 제외합니다.
# 또한 torch 가 실제로 설치된 파이썬인지 확인한 뒤 선택합니다.
$후보목록 = @()
$후보목록 += Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\pythonw.exe" -ErrorAction SilentlyContinue |
             Sort-Object FullName -Descending | ForEach-Object { $_.FullName }
$후보목록 += Get-ChildItem "C:\Python3*\pythonw.exe" -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
$명령경로 = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if ($명령경로 -and $명령경로 -notmatch "WindowsApps") {
    $후보목록 += (Join-Path (Split-Path -Parent $명령경로) "pythonw.exe")
}

$파이썬창없음 = $null
foreach ($후보 in ($후보목록 | Where-Object { $_ } | Select-Object -Unique)) {
    if (-not (Test-Path $후보)) { continue }
    if ($후보 -match "WindowsApps") { continue }
    # 같은 폴더의 python.exe 로 torch 가 설치돼 있는지 검사합니다.
    $검사용 = Join-Path (Split-Path -Parent $후보) "python.exe"
    if (-not (Test-Path $검사용)) { continue }
    & $검사용 -c "import torch" 2>$null
    if ($LASTEXITCODE -eq 0) { $파이썬창없음 = $후보; break }
    if (-not $파이썬창없음) { $파이썬창없음 = $후보 }   # torch 가 없어도 마지막 후보로 보관
}
if (-not $파이썬창없음) {
    Write-Error "pythonw.exe 를 찾지 못했습니다. 파이썬 설치 경로를 확인해 주세요."
    exit 1
}
Write-Host "사용할 실행 파일: $파이썬창없음"

# --- 2) 바탕 화면에 바로가기(.lnk) 만들기 ----------------------------------
$바탕화면 = [Environment]::GetFolderPath("Desktop")
$바로가기경로 = Join-Path $바탕화면 $바로가기이름

$쉘 = New-Object -ComObject WScript.Shell
$바로가기 = $쉘.CreateShortcut($바로가기경로)
$바로가기.TargetPath = $파이썬창없음
$바로가기.Arguments = '"' + $실행스크립트 + '"'
$바로가기.WorkingDirectory = $프로젝트폴더
$바로가기.Description = "마우스로 쓴 손글씨 숫자를 인식합니다 (MNIST CNN)"
$바로가기.WindowStyle = 1
if (Test-Path $아이콘경로) { $바로가기.IconLocation = "$아이콘경로,0" }
$바로가기.Save()
Write-Host "바로가기를 만들었습니다: $바로가기경로"

# --- 3) 바로가기에 앱 식별자(AppUserModelID) 기록하기 ----------------------
# 이 값이 있어야 작업 표시줄에 고정한 아이콘과 실행 중인 창이 하나로 묶입니다.
$C샵코드 = @'
using System;
using System.Runtime.InteropServices;

public static class 바로가기속성 {
    [ComImport, Guid("00021401-0000-0000-C000-000000000046")]
    private class ShellLink { }

    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown),
     Guid("0000010b-0000-0000-C000-000000000046")]
    private interface IPersistFile {
        void GetClassID(out Guid pClassID);
        [PreserveSig] int IsDirty();
        void Load([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, int dwMode);
        void Save([MarshalAs(UnmanagedType.LPWStr)] string pszFileName,
                  [MarshalAs(UnmanagedType.Bool)] bool fRemember);
        void SaveCompleted([MarshalAs(UnmanagedType.LPWStr)] string pszFileName);
        void GetCurFile([MarshalAs(UnmanagedType.LPWStr)] out string ppszFileName);
    }

    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    private struct PROPERTYKEY {
        public Guid fmtid;
        public uint pid;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct PROPVARIANT {
        public ushort vt;
        public ushort r1, r2, r3;
        public IntPtr p1;
        public IntPtr p2;
    }

    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown),
     Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99")]
    private interface IPropertyStore {
        void GetCount(out uint cProps);
        void GetAt(uint iProp, out PROPERTYKEY pkey);
        void GetValue(ref PROPERTYKEY key, out PROPVARIANT pv);
        void SetValue(ref PROPERTYKEY key, ref PROPVARIANT pv);
        void Commit();
    }

    private const ushort VT_LPWSTR = 31;

    [DllImport("ole32.dll", PreserveSig = false)]
    private static extern void PropVariantClear(ref PROPVARIANT pvar);

    // System.AppUserModel.ID 속성 키
    private static readonly Guid AppUserModelGuid =
        new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3");

    public static void 식별자설정(string 바로가기경로, string 식별자) {
        object 링크 = new ShellLink();
        ((IPersistFile)링크).Load(바로가기경로, 2 /* STGM_READWRITE */);

        PROPERTYKEY 키 = new PROPERTYKEY();
        키.fmtid = AppUserModelGuid;
        키.pid = 5;

        // 문자열 값을 담은 PROPVARIANT 를 직접 구성합니다. (vt = VT_LPWSTR)
        PROPVARIANT 값 = new PROPVARIANT();
        값.vt = VT_LPWSTR;
        값.p1 = Marshal.StringToCoTaskMemUni(식별자);
        try {
            IPropertyStore 저장소 = (IPropertyStore)링크;
            저장소.SetValue(ref 키, ref 값);
            저장소.Commit();
            ((IPersistFile)링크).Save(바로가기경로, true);
        } finally {
            PropVariantClear(ref 값);
            Marshal.ReleaseComObject(링크);
        }
    }
}
'@

try {
    if (-not ("바로가기속성" -as [type])) { Add-Type -TypeDefinition $C샵코드 -Language CSharp }
    [바로가기속성]::식별자설정($바로가기경로, $앱식별자)
    Write-Host "앱 식별자를 기록했습니다: $앱식별자"
} catch {
    Write-Warning "앱 식별자 기록에 실패했습니다(바로가기 자체는 정상 동작): $($_.Exception.Message)"
}

# --- 4) 시작 메뉴에도 복사 (검색 및 고정이 쉬워집니다) ---------------------
$시작메뉴 = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
Copy-Item -Path $바로가기경로 -Destination (Join-Path $시작메뉴 $바로가기이름) -Force
Write-Host "시작 메뉴에도 등록했습니다: $시작메뉴\$바로가기이름"

Write-Host ""
Write-Host "완료되었습니다. 바탕 화면의 '손글씨 숫자 인식기' 를 더블 클릭해 보세요."
Write-Host "작업 표시줄 고정: 바로가기에서 마우스 오른쪽 클릭 → (추가 옵션 표시 →) 작업 표시줄에 고정"
