<table_of_contents color="gray"/>
<empty-block/>
# 설계 목표
FPGA Kit의 7 Segment 모듈과 Keypad 모듈을 이용해 비밀번호 입력과 인증이 가능한 디지털 도어락을 Verilog로 설계한다. 숫자 키로 최대 6자리 비밀번호를 입력해 7 Segment에 표시하고, 확인 키를 누르면 저장된 비밀번호와 비교해 일치하면 OPEN, 일치하지 않으면 ERROR를 띄우며, 3회 연속으로 틀리면 일정 시간 동안 입력을 막는 LOCK 상태로 전환한다. 비밀번호 변경과 초기화, 6자리 초과 입력이나 빈 입력 확인 같은 예외 처리를 모두 구현하고, 추가 구현으로 입력 편집(Backspace, Clear), LOCK 남은 시간 표시와 잠금 시간 점증, 새 비밀번호 두 번 확인 입력을 완성한다.
<empty-block/>
<empty-block/>
# 과제 요구사항 분석 및 구현 방안
## 요구사항 정의
<table header-row="true">
<tr>
<td>R</td>
<td>요구사항</td>
<td>구현 방안</td>
</tr>
<tr>
<td>R1</td>
<td>숫자 버튼(0\~9)으로 최대 6자리 비밀번호를 입력하고, 입력한 숫자를 7 Segment에 표시한다</td>
<td>숫자 키를 누를 때마다 입력 버퍼(4비트 6칸과 길이)에 왼쪽부터 채우고 같은 자리에 숫자를 띄운다. 여섯 자리가 찬 뒤에 또 누르면 맨 앞 숫자를 버리고 왼쪽으로 한 칸씩 밀어 마지막 여섯 개만 남긴다</td>
</tr>
<tr>
<td>R2</td>
<td>"확인" 버튼을 누르면 비밀번호를 검증한다</td>
<td>OK(pb12)를 누르면 CHECK 상태에서 입력 버퍼와 저장된 비밀번호를 길이까지 함께 비교한다</td>
</tr>
<tr>
<td>R3</td>
<td>미리 설정된 비밀번호와 일치하면 "OPEN"을 표시한다</td>
<td>OPEN 상태로 가서 "OPEn"을 띄우고, 실패 횟수를 0으로 되돌린다. 7 Segment로는 N을 대문자로 그릴 수 없어 소문자 n을 쓴다</td>
</tr>
<tr>
<td>R4</td>
<td>비밀번호가 일치하지 않으면 "ERROR"를 표시한다</td>
<td>실패 횟수를 1 올린다. 1, 2회째 오답이면 "Error"를 1.5초 띄운 뒤 입력 대기로 돌아가고, 3회째 오답이면 R5대로 LOCK으로 간다. 7 Segment로는 R을 대문자로 그릴 수 없어 소문자 r을 쓴다</td>
</tr>
<tr>
<td>R5</td>
<td>잘못된 비밀번호를 3회 연속 입력하면 LOCK 상태가 된다(입력 불가, 일정 시간 이후 재입력 가능)</td>
<td>세 번째 오답에서 LOCK으로 가서 모든 키를 무시하고, 잠금 시간이 끝나면 실패 횟수와 입력 버퍼를 비우고 입력 대기로 돌아간다</td>
</tr>
<tr>
<td>R6</td>
<td>비밀번호를 변경할 수 있다</td>
<td>OPEN에서 CHG(pb3)를 누르면 새 비밀번호를 4\~6자리로 두 번 입력받아, 두 입력이 같을 때만 저장한다(두 번 확인은 추가 구현 A3)</td>
</tr>
<tr>
<td>R7</td>
<td>비밀번호를 초기화할 수 있다</td>
<td>OPEN에서 RST(pb7)를 누르면 비밀번호를 기본값 "1234"로 되돌리고 "InIt"를 띄운다</td>
</tr>
<tr>
<td>R8</td>
<td>6자리를 넘는 입력, 비밀번호 없이 확인을 누르는 경우 등의 예외를 처리한다</td>
<td>6자리를 넘겨 누르면 마지막에 누른 여섯 숫자만 남기고, 빈 입력에서 OK를 누르면 "nonE"를 띄우고 오답 1회로 센다. 항목별 동작은 아래 평가 항목 표에 정리했다</td>
</tr>
</table>
<empty-block/>
## 평가 항목별 동작
<table header-row="true">
<tr>
<td>E</td>
<td>평가 항목</td>
<td>동작</td>
<td>관련 R</td>
</tr>
<tr>
<td>E1</td>
<td>비밀번호가 맞으면 열리고, 틀리면 ERROR가 나는지</td>
<td>맞으면 "OPEn", 틀리면 "Error"를 1.5초 띄우고 입력 대기로 돌아간다. 3회째 오답은 E2를 따른다</td>
<td>R2, R3, R4</td>
</tr>
<tr>
<td>E2</td>
<td>잘못된 비밀번호를 3회 연속 입력하면 LOCK 상태가 되는지</td>
<td>실패 횟수가 2인 상태에서 또 틀리면 "Error"를 거치지 않고 바로 LOCK으로 간다. 표시는 "LOCK10"부터 1초마다 줄어든다</td>
<td>R5</td>
</tr>
<tr>
<td>E3</td>
<td>1번째 LOCK 이후 2번째 LOCK이 작동하는지</td>
<td>LOCK이 풀릴 때 실패 횟수를 0으로 되돌리므로 다시 세 번 틀리면 같은 경로로 LOCK에 들어간다. 그 사이 한 번도 맞히지 않았다면 두 번째 잠금은 20초다</td>
<td>R5</td>
</tr>
<tr>
<td>E4</td>
<td>비밀번호 변경 시 이전 비밀번호를 입력했을 때의 동작</td>
<td>변경이 끝나면 저장값이 새 비밀번호로 바뀌므로 이전 비밀번호는 "Error"가 되고 오답 1회로 센다. 변경 도중 새 비밀번호 자리에 이전 비밀번호와 같은 값을 넣으면 4\~6자리이고 확인 입력과 같으면 그대로 저장한다</td>
<td>R6</td>
</tr>
<tr>
<td>E5</td>
<td>아무 숫자도 입력하지 않고 OK를 누르는 경우</td>
<td>"nonE"를 1.5초 띄우고 입력 대기로 돌아가며 오답 1회로 센다. "nonE"는 숫자를 넣지 않았다는 안내다. 세 번째 오답이면 "nonE"를 거치지 않고 바로 LOCK으로 간다</td>
<td>R5, R8</td>
</tr>
<tr>
<td>E6</td>
<td>비밀번호 변경에서 새 비밀번호를 하나도 안 넣고 OK를 누른 경우</td>
<td>"Error"를 띄우고 비밀번호는 그대로 둔 채 OPEN으로 돌아간다. 0\~3자리를 모두 길이 미달로 보므로 1\~3자리만 넣고 OK를 눌러도 같다. 실패 횟수는 CHECK에서만 올리므로 변하지 않는다</td>
<td>R6, R8</td>
</tr>
<tr>
<td>E7</td>
<td>비밀번호 초기화 기능</td>
<td>OPEN에서 RST를 누르면 "InIt"를 띄우고, 이후 "1234"로 열린다</td>
<td>R7</td>
</tr>
<tr>
<td>E8</td>
<td>비밀번호 6자리 초과 입력</td>
<td>마지막에 누른 여섯 숫자만 버퍼에 남기고 표시도 왼쪽으로 민다. "1234567"을 누르면 "234567"이 뜨고, OK를 누르면 이 여섯 숫자를 저장된 비밀번호와 비교한다</td>
<td>R1, R8</td>
</tr>
<tr>
<td>E9</td>
<td>LOCK 상태에서 코드에 입력한 시간까지 모든 입력을 무시하는지, LOCK 해제 직후 비밀번호 입력이 정상적으로 가능한지</td>
<td>코드에 입력한 잠금 시간은 LOCK_SEC=10초이고, 한 번도 맞히지 않은 채 다시 잠기면 20초, 40초가 된다(A2). 이 시간이 끝날 때까지 키 입력을 받지 않으며 남은 초를 오른쪽 두 자리에 띄운다. 키는 누르는 순간 한 번만 들어오므로 잠금 중에 이미 인식된 키는 누르고 있어도 해제 뒤에 입력되지 않는다. 해제되면 "------"로 돌아가 바로 입력할 수 있다</td>
<td>R5</td>
</tr>
<tr>
<td>E10</td>
<td>OPEN, 비밀번호 변경, 비밀번호 틀림 이후 다시 비밀번호가 변경되는지</td>
<td>변경이 끝나면 입력 대기(IDLE)로 돌아가 문이 닫힌다. 입력 대기에서는 CHG를 무시하고, 새 비밀번호로 다시 열면 OPEN에서 다시 변경할 수 있다. 문을 열 때 틀려도 LOCK이 아니면 바로 다시 입력할 수 있고, 변경 중 확인 입력이 달라 "Error"가 뜨면 OPEN으로 돌아가 CHG로 다시 변경할 수 있다</td>
<td>R6</td>
</tr>
</table>
<empty-block/>
## 키 배치
<table header-row="true">
<tr>
<td></td>
<td>열0</td>
<td>열1</td>
<td>열2</td>
<td>열3</td>
</tr>
<tr>
<td>행0</td>
<td>1 (pb0)</td>
<td>2 (pb1)</td>
<td>3 (pb2)</td>
<td>변경 CHG (pb3)</td>
</tr>
<tr>
<td>행1</td>
<td>4 (pb4)</td>
<td>5 (pb5)</td>
<td>6 (pb6)</td>
<td>초기화 RST (pb7)</td>
</tr>
<tr>
<td>행2</td>
<td>7 (pb8)</td>
<td>8 (pb9)</td>
<td>9 (pb10)</td>
<td>예비 (pb11)</td>
</tr>
<tr>
<td>행3</td>
<td>확인 OK (pb12)</td>
<td>0 (pb13)</td>
<td>지우기 BS (pb14)</td>
<td>전체 지우기 CLR (pb15)</td>
</tr>
</table>
숫자 키는 실제 도어락처럼 왼쪽 위부터 1\~9를 두고 0을 맨 아래 가운데에 둔다. 기능 키는 오른쪽 열과 맨 아래 줄에 모았고 pb11은 쓰지 않는다. 키패드의 16개 입력은 눌렀을 때 0이 되므로 반전해서 쓴다.
<empty-block/>
## 상태와 표시
- **상태별 표시와 전이**
	<table header-row="true">
<tr>
<td>상태</td>
<td>표시</td>
<td>전이</td>
</tr>
<tr>
<td>IDLE (입력 대기)</td>
<td>"------", 숫자를 누르면 왼쪽부터 채운다</td>
<td>숫자는 버퍼에 넣고(마지막 6개만 남긴다), OK는 CHECK로, BS와 CLR은 버퍼를 고친다</td>
</tr>
<tr>
<td>CHECK</td>
<td>없음(1클록)</td>
<td>일치하면 OPEN. 불일치하면 실패 횟수를 올리고 3회째면 LOCK, 아니면 "Error" 후 IDLE. 버퍼가 비었으면 불일치와 똑같이 세고 "Error" 대신 "nonE"를 띄운다</td>
</tr>
<tr>
<td>OPEN</td>
<td>"OPEn"</td>
<td>OK는 IDLE(문 닫힘), CHG는 NEW_PW, RST는 "1234"로 복원하고 "InIt" 후 IDLE</td>
</tr>
<tr>
<td>NEW_PW</td>
<td>"nEW", 숫자를 누르면 입력 숫자로 바뀐다</td>
<td>숫자, BS, CLR은 버퍼를 고친다. 4\~6자리에서 OK는 NEW_CONFIRM, 0\~3자리에서 OK는 "Error" 후 OPEN</td>
</tr>
<tr>
<td>NEW_CONFIRM</td>
<td>"AGAIn", 숫자를 누르면 입력 숫자로 바뀐다</td>
<td>숫자, BS, CLR은 버퍼를 고친다. OK를 누르면 첫 입력과 길이까지 비교해 같으면 저장하고 "donE" 후 IDLE, 빈 입력을 포함해 다르면 "Error" 후 OPEN(비밀번호 유지, 실패 횟수 그대로)</td>
</tr>
<tr>
<td>MSG</td>
<td>"Error", "nonE", "donE", "InIt" 중 하나</td>
<td>1.5초 동안 키를 무시하고 정해 둔 다음 상태로 간다</td>
</tr>
<tr>
<td>LOCK</td>
<td>"LOCK"과 남은 초 2자리(예 "LOCK09")</td>
<td>모든 키를 무시한다. "LOCK01"을 1초 띄운 뒤 "LOCK00" 없이 실패 횟수를 0으로, 버퍼를 비우고 IDLE</td>
</tr>
	</table>
입력은 1\~6자리이고 6자리를 넘겨 누르면 마지막 여섯 숫자만 남는다. 밀려난 숫자는 BS를 눌러도 되살아나지 않으며, 새 비밀번호 입력과 확인 입력에도 같은 규칙을 쓴다. 새 비밀번호는 4\~6자리이고, 기본값과 초기화값은 "1234"다. 잠금 시간은 LOCK_SEC=10에서 시작해 잠길 때마다 늘어난다(추가 구현 A2). 메시지는 1.5초 동안 띄운다. 두 시간 모두 door_fsm이 LOCK이나 MSG에 들어갈 때 0부터 50MHz 클록을 세어 잰다. 키 입력은 10ms 간격으로 두 번 같은 값이 읽혀야 받아들이고, 7 Segment 여섯 자리는 1kHz로 한 자리씩 돌아가며 켠다. 시간 상수는 LOCK_SEC과 1초의 클록 수를 parameter로 따로 두고, 10ms, 1kHz, 1.5초는 1초의 클록 수에서 계산한다. 시뮬레이션에서는 1초의 클록 수만 줄이고 "LOCK10" 같은 표시는 그대로 둔다.
표에 없는 키는 모두 무시한다. 입력 대기의 CHG와 RST, OPEN에서 숫자와 BS, CLR, 변경 중의 CHG와 RST, 쓰지 않는 pb11이 여기에 든다.
입력 버퍼는 IDLE, NEW_PW, NEW_CONFIRM에 들어갈 때마다 비운다. NEW_PW에서 받은 첫 번째 새 비밀번호와 그 길이는 버퍼를 비우기 전에 따로 보관해 확인 입력과 길이까지 비교한다.
화면 여섯 자리는 왼쪽부터 1\~6번이고, 메시지가 여섯 글자보다 짧으면 왼쪽부터 쓰고 남은 자리는 끈다. 숫자를 입력하는 동안 아직 누르지 않은 자리는 "-"로 둔다. NEW_PW와 NEW_CONFIRM에서 입력을 모두 지우면 다시 "nEW"와 "AGAIn"을 띄운다.
- **화면 여섯 자리**
	<table header-row="true">
<tr>
<td>화면</td>
<td>1</td>
<td>2</td>
<td>3</td>
<td>4</td>
<td>5</td>
<td>6</td>
</tr>
<tr>
<td>입력 없음 "------"</td>
<td>-</td>
<td>-</td>
<td>-</td>
<td>-</td>
<td>-</td>
<td>-</td>
</tr>
<tr>
<td>"12"까지 입력</td>
<td>1</td>
<td>2</td>
<td>-</td>
<td>-</td>
<td>-</td>
<td>-</td>
</tr>
<tr>
<td>"OPEn"</td>
<td>O</td>
<td>P</td>
<td>E</td>
<td>n</td>
<td>끔</td>
<td>끔</td>
</tr>
<tr>
<td>"Error"</td>
<td>E</td>
<td>r</td>
<td>r</td>
<td>o</td>
<td>r</td>
<td>끔</td>
</tr>
<tr>
<td>"nonE"</td>
<td>n</td>
<td>o</td>
<td>n</td>
<td>E</td>
<td>끔</td>
<td>끔</td>
</tr>
<tr>
<td>"donE"</td>
<td>d</td>
<td>o</td>
<td>n</td>
<td>E</td>
<td>끔</td>
<td>끔</td>
</tr>
<tr>
<td>"InIt"</td>
<td>I</td>
<td>n</td>
<td>I</td>
<td>t</td>
<td>끔</td>
<td>끔</td>
</tr>
<tr>
<td>"nEW"</td>
<td>n</td>
<td>E</td>
<td>W</td>
<td>끔</td>
<td>끔</td>
<td>끔</td>
</tr>
<tr>
<td>"AGAIn"</td>
<td>A</td>
<td>G</td>
<td>A</td>
<td>I</td>
<td>n</td>
<td>끔</td>
</tr>
<tr>
<td>"LOCK"과 남은 9초</td>
<td>L</td>
<td>O</td>
<td>C</td>
<td>K</td>
<td>0</td>
<td>9</td>
</tr>
	</table>
<empty-block/>
## 추가 구현
<table header-row="true">
<tr>
<td>A</td>
<td>기능</td>
<td>동작</td>
<td>완료 기준</td>
</tr>
<tr>
<td>A1</td>
<td>입력 편집(Backspace, Clear)</td>
<td>BS(pb14)는 마지막 숫자 하나를 지우고 CLR(pb15)은 입력을 모두 지운다. 입력 대기, 새 비밀번호 입력, 확인 입력에서만 동작하고 빈 입력에서 BS는 아무 일도 하지 않는다</td>
<td>입력 대기에서 "123"을 넣고 BS를 누르면 "12----"가 되고, CLR을 누르면 "------"로 돌아간다</td>
</tr>
<tr>
<td>A2</td>
<td>LOCK 남은 시간 표시와 잠금 시간 점증</td>
<td>LOCK 동안 남은 초를 오른쪽 두 자리에 1초마다 줄여 표시하고, 잠길 때마다 잠금 시간을 10→20→40초(LOCK_SEC의 1, 2, 4배)로 늘린다. 40초에서 멈추고 한 번 맞히면 10초로 돌아간다</td>
<td>맞히지 않고 다시 잠기면 "LOCK20"부터, 세 번째와 네 번째는 "LOCK40"부터 1초마다 줄고, 한 번 맞힌 뒤에는 "LOCK10"부터 시작한다</td>
</tr>
<tr>
<td>A3</td>
<td>새 비밀번호 두 번 확인</td>
<td>변경할 때 새 비밀번호를 두 번 입력받아 같을 때만 저장한다</td>
<td>두 번째 입력을 다르게 넣으면 "Error"가 뜨고, 이후에도 기존 비밀번호로만 열린다</td>
</tr>
</table>
Backspace와 Clear는 둘 다 입력을 고치는 기능이라 하나로 묶었다.
<empty-block/>
<empty-block/>
# 예상 문제점 및 해결 방안
<table header-row="true">
<tr>
<td>문제</td>
<td>해결 방안</td>
<td>근거</td>
</tr>
<tr>
<td>키를 한 번 눌러도 접점이 떨려(채터링) 여러 번 눌린 것으로 읽힐 수 있고, 두 키를 동시에 누르면 어느 키인지 정할 수 없다</td>
<td>10ms 간격으로 두 번 읽어 같을 때만 받고, 아무 키도 눌리지 않은 상태에서 한 키만 눌릴 때만 입력으로 인정한다. 누른 채 다른 키를 더 누르거나 두 키를 함께 누르면 모두 뗄 때까지 받지 않는다. 누르는 순간에만 key_valid를 1클록 낸다</td>
<td>예제 코드도 눌린 키가 없던 상태에서 새로 눌린 입력을 두 번 연속 읽어 비교한다(example.v 82\~89행)</td>
</tr>
<tr>
<td>키패드 입력은 50MHz 클록과 상관없이 바뀌므로 플립플롭이 준안정 상태에 빠질 수 있다</td>
<td>입력을 플립플롭 두 단으로 동기화한 뒤 쓴다</td>
<td>버튼 신호가 FPGA 핀으로 바로 들어온다</td>
</tr>
<tr>
<td>예제 코드는 카운터 비트 init_counter\[20\]과 init_counter\[16\]을 클록으로 써서 클록이 셋으로 나뉘고, 그 사이로 신호가 오갈 때 타이밍을 보장하기 어렵다</td>
<td>모든 플립플롭을 50MHz 클록 하나로 돌리고, 키를 읽는 간격과 자리를 바꾸는 간격은 tick_gen이 만드는 1클록짜리 enable 틱으로, LOCK과 메시지 시간은 door_fsm의 카운터로 잰다</td>
<td>example.v 69\~73행, 81행, 822행</td>
</tr>
<tr>
<td>예제 코드의 감지 목록 없는 always 블록은 시뮬레이터에서 시간이 흐르지 않는 무한 반복이 되어 시뮬레이션이 멈춘다</td>
<td>키 입력 반전은 assign 연속 할당으로 바꾸고 나눈 클록은 만들지 않는다</td>
<td>example.v 69\~73행</td>
</tr>
<tr>
<td>핀맵에 리셋 핀이 없어 처음 상태로 되돌릴 방법이 없고, 초기값이 없는 레지스터는 시뮬레이션에서 값이 정해지지 않는다</td>
<td>por 모듈의 카운터는 선언할 때 초기값 0을 주고, 전원을 넣은 뒤 일정 클록 동안 rst를 유지해 나머지 레지스터를 초기값(비밀번호 "1234", 실패 횟수 0)으로 만든다</td>
<td>핀맵에 clock_50m, fnd_d, fnd_s, pb만 있다</td>
</tr>
<tr>
<td>여섯 자리를 돌아가며 켤 때 자리를 바꾸는 순간 앞 자리의 세그먼트가 다음 자리에 잠깐 비치는 잔상이 생길 수 있다</td>
<td>자리를 바꿀 때 세그먼트를 잠깐 모두 끈 뒤 다음 자리를 켠다</td>
<td>여섯 자리가 세그먼트 선 fnd_d\[7:0\]를 함께 쓴다</td>
</tr>
<tr>
<td>K, W는 7 Segment로 정확히 그릴 수 없고 G는 6과 비슷하다</td>
<td>가장 비슷한 모양으로 대신하고 보드에서 읽히는지 확인한다</td>
<td>세그먼트가 7개뿐이다</td>
</tr>
<tr>
<td>LOCK 10초나 메시지 1.5초를 50MHz 시뮬레이션에서 그대로 기다리면 너무 오래 걸린다</td>
<td>시간 상수를 parameter로 두고 테스트벤치에서만 1초의 클록 수를 작은 값으로 바꾼다</td>
<td>10초는 5억 클록이다</td>
</tr>
</table>
<empty-block/>
## 검증 방법
시간 상수를 parameter로 줄인 Questa 테스트벤치에서 평가 항목 E1\~E10과 추가 구현 A1\~A3의 키 입력을 순서대로 재생하고, 입력은 최상위 모듈의 pb에 넣어 디바운스까지 함께 검증하며, 단계마다 화면에 나갈 여섯 글자를 기대값과 비교한다. 시뮬레이션이 모두 맞으면 보드에 올려 같은 순서로 직접 눌러 보고, 7 Segment 글자 모양과 키 반응처럼 시뮬레이션으로 볼 수 없는 것은 보드에서 확인한다. 보드에서는 각 키가 쓰이는 상태에서 pb11을 뺀 15개 키를 10번씩 눌러 매번 한 번씩 반응하고, pb11은 아무 반응이 없고, 화면 표의 글자를 모두 읽을 수 있고, 잔상이 보이지 않으면 통과로 본다.
<empty-block/>
<empty-block/>
# 프로젝트 동작 블록 다이어그램
## 모듈 블록 다이어그램
![그림 1. 모듈 블록 다이어그램](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/756b812a-087a-401a-9f4c-7dd4c4fbaa37/%EB%B8%94%EB%A1%9D%EB%8B%A4%EC%9D%B4%EC%96%B4%EA%B7%B8%EB%9E%A8.png)
키패드 입력 pb\[15:0\]은 key_input에서 반전, 동기화, 디바운스를 거쳐 한 번 누를 때마다 key_valid 한 클록과 키 번호가 되고, key_decode가 이를 숫자 0\~9와 OK, CHG, RST, BS, CLR로 바꿔 key_valid와 같은 클록에 door_fsm으로 넘긴다. door_fsm은 이 키로 상태를 바꾸면서 입력 버퍼, 비밀번호, 실패 횟수, 잠금 시간을 관리하고, 현재 상태, 메시지 종류, 입력 버퍼(24비트)와 길이(3비트), 십진 두 자리로 바꾼 남은 초를 display_ctrl에 넘긴다. display_ctrl이 이를 여섯 글자로 만들면 seg_driver가 7 Segment에 한 자리씩 돌아가며 내보낸다. 모든 모듈은 clock_50m 하나로 동작하며, tick_gen이 만드는 10ms 틱과 1kHz 틱으로 키를 읽는 간격과 자리를 바꾸는 간격을 맞추고 por 모듈이 전원을 넣은 직후 나머지 모듈을 초기화한다.
<empty-block/>
## 상태도
![그림 2. door_fsm 상태도](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/f9961b4d-51c7-4777-b6ed-f0107b7a7a6a/%EC%83%81%ED%83%9C%EB%8F%84.png)
변경은 OPEN에서만 시작되고, NEW_PW와 NEW_CONFIRM 두 단계를 거쳐야 저장된다. 각 상태의 표시와 전이 조건은 상태와 표시 표에 정리했다.
<empty-block/>
## 키패드 그림
![그림 3. 키패드 키 배치](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/e0f520f9-2167-45f8-9dca-c1221d2f5553/%ED%82%A4%EB%B0%B0%EC%B9%98.png)
각 키의 pb 번호는 키 배치 표와 같다.
<empty-block/>
<empty-block/>
# 조원 역할 분담
## 담당
<table header-row="true">
<tr>
<td>조원</td>
<td>담당 모듈</td>
<td>담당 작업</td>
</tr>
<tr>
<td>신현준</td>
<td>key_input, key_decode, door_fsm, display_ctrl, seg_driver, tick_gen, por, 최상위 모듈</td>
<td>전체 모듈 설계, 최상위 모듈 연결과 핀 배치, Questa 테스트벤치 작성, 모듈별 시뮬레이션과 E1\~E10, A1\~A3 통합 시뮬레이션</td>
</tr>
<tr>
<td>최승민</td>
<td>-</td>
<td>보드 시연</td>
</tr>
</table>
<empty-block/>
## 일정
<table header-row="true">
<tr>
<td>날짜</td>
<td>목표</td>
</tr>
<tr>
<td>11/27</td>
<td>모듈별 시뮬레이션 완료</td>
</tr>
<tr>
<td>12/4</td>
<td>보드 통합, E1\~E10과 추가 구현 점검</td>
</tr>
<tr>
<td>12/11</td>
<td>구두 평가</td>
</tr>
<tr>
<td>12/23</td>
<td>설계 보고서 제출</td>
</tr>
</table>
<empty-block/>
<empty-block/>
# 조교님께 확인한 사항
평가 항목의 해석이 갈리는 부분을 조교님께 여쭈어 확정하고 설계에 반영했다.
- **조교님 답변과 반영**
	<table header-row="true">
<tr>
<td>확인한 내용</td>
<td>조교님 답변</td>
<td>반영한 곳</td>
</tr>
<tr>
<td>"비밀번호 변경 시 이전 비밀번호를 입력했을 때"의 뜻</td>
<td>변경을 마친 뒤 이전 비밀번호로 문을 열려고 하는 경우다</td>
<td>E4</td>
</tr>
<tr>
<td>"비밀번호 틀림 이후 다시 비밀번호가 변경되는지"에서 변경 뒤 문을 열 때 틀린 경우와 변경 중 확인 입력이 다른 경우 모두 다시 변경할 수 있게 한 것</td>
<td>그대로 진행하면 된다. 확인 입력이 다르면 열린 상태(OPEN)로 돌아가 바로 다시 변경해도 된다</td>
<td>E10</td>
</tr>
<tr>
<td>비밀번호 초기화를 허용하는 상태</td>
<td>OPEN 상태에서만 가능하게 한다</td>
<td>R7, E7</td>
</tr>
<tr>
<td>입력 대기에서 아무 숫자 없이 OK를 누른 경우</td>
<td>오답으로 처리한다</td>
<td>R8, E5</td>
</tr>
<tr>
<td>6자리를 넘겨 입력한 경우</td>
<td>마지막으로 입력된 6개의 숫자를 받는다</td>
<td>R1, R8, E8</td>
</tr>
<tr>
<td>잠금 시간을 10초, 20초, 40초로 늘리는 것</td>
<td>일정 시간 이상이면 상관없다</td>
<td>A2</td>
</tr>
	</table>
<empty-block/>
<empty-block/>
# 출처 및 참고문헌
- 논리회로실험 설계과제 공지 (2026-2)
- 논리회로실험 설계 환경구축 및 실습
- \[추가자료\] 7 Segment 출력개수 수정 방법
- \[추가자료\] pin map 작성법
- 설계 자료 예제 코드(example.v)와 FPGA pin map