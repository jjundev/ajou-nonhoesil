<table_of_contents color="gray"/>
<empty-block/>
# 실험 목적
논리 기호로만 다루던 CMOS 소자가 실제 전압과 시간의 눈금에서 어떻게 동작하는지 확인하는 것이 이번 실험의 목적이다. 강의노트는 목표를 논리 소자의 논리 레벨(L 또는 H) 판정, 슈미트 트리거 인버터의 동작 원리, CMOS 회로의 전기적 특성, 그리고 CMOS의 DC·AC·스위칭 특성 네 가지로 든다.
실험은 74HC04 인버터 한 개에 사인파를 넣고 오실로스코프를 X-Y 모드로 두어 입력 전압에 대한 출력 전압 곡선을 화면에 그리는 데서 시작한다. 같은 자리에 74HC14 슈미트 트리거 인버터를 갈아 끼워 두 곡선을 비교한다. 마지막으로 74HC04의 여섯 인버터를 직렬로 잇고 1MHz 사각파를 넣어 전달 지연 tpd를 재고, 데이터시트 값과 비교한다.
<empty-block/>
<empty-block/>
# 실험 이론
## 논리 레벨 판정과 잡음 여유
논리 소자가 입력을 HIGH와 LOW로 판정하는 경계는 한 점이 아니라 띠다. 강의노트는 VCC와 GND 사이를 네 전압으로 나눈다.
- VOHmin: HIGH를 출력할 때의 최소 허용 전압
- VIHmin: HIGH로 입력받을 때의 최소 입력 전압
- VILmax: LOW로 입력받을 때의 최대 입력 전압
- VOLmax: LOW를 출력할 때의 최대 허용 전압
출력 규격이 입력 규격보다 안쪽에 있어서, 앞단 출력이 VOHmin 이상이면 배선에서 VOHmin과 VIHmin의 차만큼 전압이 깎여도 다음 단이 HIGH로 읽는다. LOW 쪽도 마찬가지로 VILmax와 VOLmax의 차만큼 여유가 있다. 이 두 간격이 DC 잡음 여유다. VILmax와 VIHmin 사이는 ABNORMAL 구간으로, 여기 머무는 입력은 HIGH도 LOW도 아니어서 출력이 어느 쪽일지 보장되지 않는다.
실험 1-1에서 X-Y 화면에 그려지는 곡선이 이 정의를 그대로 보여 준다. 입력이 VILmax 아래에 있는 동안 출력은 VCC 근처에 머물고, VIHmin을 넘으면 GND 근처로 내려간다.
<empty-block/>
## CMOS 인버터의 구조
CMOS 인버터는 VCC 쪽의 PMOS와 GND 쪽의 NMOS가 직렬로 놓인 구조다. 입력이 LOW면 PMOS만 켜져 출력을 VCC로 끌어올리고, 입력이 HIGH면 NMOS만 켜져 출력을 GND로 끌어내린다. 정상 상태에서는 둘 중 하나가 반드시 꺼져 있고 꺼진 쪽의 저항은 1MΩ을 넘으므로, 출력은 VCC나 GND에 거의 붙고 정적 전류는 거의 흐르지 않는다. 실험 1-1의 곡선 양 끝이 수평인 이유가 이것이다.
켜진 쪽 트랜지스터도 이상적인 스위치가 아니라 저항으로 동작한다. 출력에 걸린 부하 커패시턴스 CL을 이 저항으로 충전하고 방전해야 하므로 출력은 입력을 즉시 따라가지 못한다. 실험 2에서 재는 전달 지연은 여기서 온다.
CMOS 입력은 임피던스가 매우 높아 아무 데도 물리지 않으면 주변 전하에 따라 ABNORMAL 구간을 떠돈다. 그러면 PMOS와 NMOS가 동시에 켜져 전류가 새고 출력이 흔들리므로, 강의노트는 쓰지 않는 입력도 반드시 VCC 또는 GND에 묶으라고 주의를 준다.
<empty-block/>
## 슈미트 트리거와 히스테리시스
보통 인버터는 문턱이 하나라 입력이 그 근처에서 잡음으로 떨리면 출력도 따라 떨린다. 슈미트 트리거 인버터는 문턱을 두 개 둔다. 입력이 올라갈 때는 VT+를 넘어야 출력이 LOW로 떨어지고, 내려갈 때는 VT- 아래로 내려가야 출력이 HIGH로 돌아온다. 두 문턱의 차가 히스테리시스 폭 VH다(VH = VT+ - VT-).
한 번 넘어간 출력은 입력이 반대쪽 문턱까지 되돌아가기 전에는 바뀌지 않으므로, VH보다 작은 잡음은 출력에 나타나지 않는다. 강의노트는 이것을 히스테리시스로 ABNORMAL 영역을 제거한 인버터라고 설명한다. 천천히 변하는 사인파를 넣어도 출력은 깨끗한 사각파가 된다.
X-Y 화면에서 보통 인버터의 곡선이 한 줄기인 것과 달리, 슈미트 트리거는 올라갈 때와 내려갈 때 전이 위치가 달라 닫힌 고리를 그린다. 고리의 오른쪽 세로 에지가 VT+, 왼쪽이 VT-, 가로 폭이 VH다.
<empty-block/>
## 전달 지연
전달 지연(propagation delay)은 입력 변화가 출력으로 전달되는 데 걸리는 시간이고, 입력과 출력이 각각 VCC의 50%를 지나는 시점 사이로 잰다. 출력이 HIGH에서 LOW로 갈 때가 tPHL, LOW에서 HIGH로 갈 때가 tPLH다. 이와 별도로 출력이 VCC의 10%와 90% 사이를 건너는 시간을 천이시간(tr, tf)이라 부르는데, 이번 실험에서 재는 것은 50% 기준의 전달 지연이지 천이시간이 아니다. 커서를 어느 높이에 놓는지가 두 값을 가른다.
인버터 한 단의 지연은 10ns 안팎이라 오실로스코프에서 한 단만 놓고 읽기에는 작다. 실험 2의 회로는 74HC04의 여섯 인버터를 모두 직렬로 잇고 체인의 두 번째 단 출력(4번 핀)과 마지막 여섯 번째 단 출력(8번 핀)을 관측한다. 두 점 사이에는 인버터 네 단이 놓이므로, 같은 방향 에지 사이의 시간은 네 단 지연의 합이다. 짝수 단이라 두 파형은 같은 방향으로 움직이고, 각 단이 tPHL과 tPLH를 번갈아 겪으므로 측정값은 2·tPHL + 2·tPLH이고 이를 4로 나눈 것이 한 단의 평균 지연이다. 데이터시트는 tpd를 tPHL과 tPLH의 공통 규격으로 두므로 그 값과 바로 견줄 수 있다.
체인 끝 8번 핀은 두 번째 74HC04의 1번 핀으로 들어간다. 이 게이트는 출력을 아무 데도 보내지 않고 체인 마지막 단의 부하 노릇만 한다.
<empty-block/>
## 데이터시트 규격값
강의노트에는 전압 규격이 실려 있지 않아 두 IC의 규격은 제조사 데이터시트에서 옮겼다. 데이터시트는 VCC 2.0V·4.5V·6.0V 세 지점에서 규정하고 이번 실험이 쓰는 5.0V 열은 없으므로, 아래 표는 5.0V에 가장 가까운 4.5V, 25°C 값이다. 4.5V 값을 5V 규격이라고 부르지는 않는다.
- **74HC04 DC 특성** (VCC 4.5V)
	<table header-row="true">
<tr>
<td>항목</td>
<td>조건</td>
<td>Min</td>
<td>Typ</td>
<td>Max</td>
<td>단위</td>
</tr>
<tr>
<td>VIH</td>
<td></td>
<td>3.15</td>
<td>2.4</td>
<td>-</td>
<td>V</td>
</tr>
<tr>
<td>VIL</td>
<td></td>
<td>-</td>
<td>2.1</td>
<td>1.35</td>
<td>V</td>
</tr>
<tr>
<td>VOH</td>
<td>IO = -20μA</td>
<td>4.4</td>
<td>4.5</td>
<td>-</td>
<td>V</td>
</tr>
<tr>
<td>VOH</td>
<td>IO = -4.0mA</td>
<td>3.98</td>
<td>4.32</td>
<td>-</td>
<td>V</td>
</tr>
<tr>
<td>VOL</td>
<td>IO = 20μA</td>
<td>-</td>
<td>0</td>
<td>0.1</td>
<td>V</td>
</tr>
<tr>
<td>VOL</td>
<td>IO = 4.0mA</td>
<td>-</td>
<td>0.15</td>
<td>0.26</td>
<td>V</td>
</tr>
	</table>
- **74HC14 문턱 전압** (VCC 4.5V)
	<table header-row="true">
<tr>
<td>항목</td>
<td>Min</td>
<td>Typ</td>
<td>Max</td>
<td>단위</td>
</tr>
<tr>
<td>VT+</td>
<td>1.7</td>
<td>2.38</td>
<td>3.15</td>
<td>V</td>
</tr>
<tr>
<td>VT-</td>
<td>0.9</td>
<td>1.4</td>
<td>2.0</td>
<td>V</td>
</tr>
<tr>
<td>VH</td>
<td>0.4</td>
<td>0.98</td>
<td>1.4</td>
<td>V</td>
</tr>
	</table>
VIH의 Min과 VIL의 Max가 보장되는 판정 경계다. 3.15V 위는 반드시 HIGH로, 1.35V 아래는 반드시 LOW로 읽히고 실제 전이는 그 사이에서 일어난다. 부하 전류가 4mA로 커지면 VOH는 내려가고 VOL은 올라가는데, 이것이 켜진 트랜지스터가 저항으로 동작한다는 앞 절의 설명이 규격에 나타난 자리다. 74HC14의 출력 전압 규격은 74HC04와 같고, 다른 것은 입력 쪽에 두 문턱이 있다는 점뿐이다.
<empty-block/>
<empty-block/>
# 실험 부품
## 준비물
<table header-row="true">
<tr>
<td>품목</td>
<td>규격</td>
<td>수량</td>
<td>비고</td>
</tr>
<tr>
<td>전압원</td>
<td>+5V</td>
<td>1</td>
<td>두 IC의 전원 핀에 공급</td>
</tr>
<tr>
<td>오실로스코프</td>
<td>2채널, 프로브 2개</td>
<td>1</td>
<td>실험 1은 X-Y 모드, 실험 2는 시간축</td>
</tr>
<tr>
<td>함수발생기</td>
<td>사인파·사각파</td>
<td>1</td>
<td>실험 1은 사인파 Vpp 5V·offset 2.5V, 실험 2는 사각파 Vpp 5V·1MHz</td>
</tr>
<tr>
<td>74HC04</td>
<td>hex inverter, DIP-14</td>
<td>2</td>
<td>실험 1-1은 한 개, 실험 2는 체인과 부하로 두 개를 동시에 쓴다</td>
</tr>
<tr>
<td>74HC14</td>
<td>hex inverting Schmitt trigger, DIP-14</td>
<td>1</td>
<td>실험 1-2에서 74HC04 자리에 갈아 끼운다</td>
</tr>
<tr>
<td>브레드보드</td>
<td></td>
<td>1</td>
<td>IC와 배선을 올린다</td>
</tr>
<tr>
<td>점퍼선</td>
<td></td>
<td>적당량</td>
<td>전원·신호 배선과 미사용 입력 처리</td>
</tr>
</table>
<empty-block/>
## 핀 배치
<table header-row="true">
<tr>
<td>IC</td>
<td>게이트1</td>
<td>게이트2</td>
<td>게이트3</td>
<td>게이트4</td>
<td>게이트5</td>
<td>게이트6</td>
<td>VCC</td>
<td>GND</td>
</tr>
<tr>
<td>74HC04 (hex inverter)</td>
<td>1 → 2</td>
<td>3 → 4</td>
<td>5 → 6</td>
<td>9 → 8</td>
<td>11 → 10</td>
<td>13 → 12</td>
<td>14</td>
<td>7</td>
</tr>
<tr>
<td>74HC14 (hex Schmitt inverter)</td>
<td>1 → 2</td>
<td>3 → 4</td>
<td>5 → 6</td>
<td>9 → 8</td>
<td>11 → 10</td>
<td>13 → 12</td>
<td>14</td>
<td>7</td>
</tr>
</table>
강의노트 회로도는 74HC04의 14핀 전부에 1A\~6Y 이름과 번호를 적어 두었고, 74HC14는 1·2·7·14번만 적혀 있다. 데이터시트로 확인하면 74HC14의 핀 배치는 74HC04와 같아서, 실험 1-2에서 배선을 하나도 바꾸지 않고 칩만 갈아 끼울 수 있다.
<empty-block/>
<empty-block/>
# 실험 과정 및 예상 결과
## 실험 1-1) Inverter의 입출력 특성 확인
74HC04의 첫 번째 게이트(1번 핀에서 2번 핀)만 쓴다. VCC에 5V를 걸고 1번 핀에 사인파 Vpp 5V, offset 2.5V를 넣는다. 오실로스코프 CH1을 1번 핀에, CH2를 2번 핀에 물리고 X-Y 모드로 바꾼다. 사인파의 offset을 2.5V로 두는 것은 입력이 0V에서 5V까지를 빠짐없이 천천히 훑게 하기 위해서다.
X-Y 모드는 시간축을 끄고 CH1을 가로축, CH2를 세로축으로 쓰므로 화면에 그려지는 것이 입력 전압에 대한 출력 전압 곡선이다. 두 파형을 시간축으로 나란히 보면 출력이 사각파라는 것만 보이고 전이가 어느 입력 전압에서 일어나는지는 읽을 수 없다.
곡선은 왼쪽 위(Vin 0V 근처, Vout 5V 근처)에서 오른쪽 아래(Vin 5V 근처, Vout 0V 근처)로 떨어지는 한 줄기로 나올 것이다. 양 끝은 거의 수평이고 가운데 전이 구간만 가파르다. 사인파가 올라갈 때와 내려갈 때의 궤적이 겹쳐 한 줄로 보이는 것이 정상이다. 전이가 일어나는 Vin 구간을 눈금으로 읽어 두고, 규격의 VILmax 1.35V와 VIHmin 3.15V 사이에 놓이는지 확인한다. 전이 중심의 정확한 값은 강의노트가 주지 않으므로 화면에서 읽은 값을 쓴다.
<empty-block/>
## 실험 1-2) Schmitt-trigger의 입출력 특성 확인
전원을 끄고 74HC04를 뽑아 같은 자리에 74HC14를 꽂는다. 배선·신호원·X-Y 모드는 실험 1-1 그대로 둔다. 두 칩의 핀 배치가 같으므로 선은 하나도 옮기지 않는다.
Vin이 올라갈 때와 내려갈 때 전이 전압이 달라 곡선이 닫힌 고리를 그릴 것이다. 고리의 오른쪽 세로 에지가 VT+, 왼쪽이 VT-이고 가로 폭이 VH다. 두 에지의 Vin 눈금을 읽어 두고, 데이터시트 범위(VCC 4.5V 기준 VT+ 1.7\~3.15V, VT- 0.9\~2.0V, VH 0.4\~1.4V) 안에 드는지 본다. 실험 1-1의 한 줄기 곡선과 나란히 놓고 보면 슈미트 트리거가 전이 구간을 어떻게 갈라 놓는지 눈으로 비교된다.
<empty-block/>
## 실험 2) CMOS의 AC 특성 확인
74HC04 두 개를 쓴다. 첫 번째 칩 U1의 여섯 인버터를 1번 핀에서 시작해 2번에서 3번, 4번에서 5번, 6번에서 13번, 12번에서 11번, 10번에서 9번 순으로 직렬로 잇고, 마지막 출력 8번 핀을 두 번째 칩 U2의 1번 핀에 넣는다. U2는 나머지 입력을 VCC 또는 GND에 묶고 출력은 모두 개방한다. VCC 5V, 1번 핀에 사각파 Vpp 5V, 1MHz를 넣는다. 오실로스코프는 시간축 모드로 되돌리고 CH1을 U1의 4번 핀, CH2를 U1의 8번 핀에 문다.
두 채널 모두 커서를 VCC의 50%인 2.5V에 놓고, CH1 에지에서 CH2의 같은 방향 에지까지의 시간을 상승·하강 각각 잰다. 1MHz면 주기가 1μs, 반주기가 500ns라 네 단 지연이 반주기 안에 여유 있게 들어와 에지 대응이 어긋나지 않는다. 측정값을 단 수 4로 나눈 것이 한 단의 지연이다.
- **전달 지연 측정** (CH1 = U1 4번 핀, CH2 = U1 8번 핀, 기준 VCC의 50%)
	<table header-row="true">
<tr>
<td>구간</td>
<td>CH1 에지 (U1 pin 4)</td>
<td>CH2 에지 (U1 pin 8)</td>
<td>측정값 (ns)</td>
<td>단 수</td>
<td>1단 환산 (ns)</td>
</tr>
<tr>
<td>상승</td>
<td>50% 상승</td>
<td>50% 상승</td>
<td></td>
<td>4</td>
<td></td>
</tr>
<tr>
<td>하강</td>
<td>50% 하강</td>
<td>50% 하강</td>
<td></td>
<td>4</td>
<td></td>
</tr>
	</table>
비교 대상은 74HC04 데이터시트의 전달 지연 규격이다. 데이터시트는 CL 50pF 부하에서 VCC 2.0V·4.5V·6.0V 세 줄을 규정하는데, 아래 표에는 실험 전원 5V에 가까운 4.5V·6.0V 두 줄만 옮겼다. 5.0V 줄은 CL 15pF의 참고값이다.
- **74HC04 데이터시트 tpd** (nA to nY, 25°C)
	<table header-row="true">
<tr>
<td>조건</td>
<td>VCC</td>
<td>CL</td>
<td>Typ (ns)</td>
<td>Max (ns)</td>
</tr>
<tr>
<td>규격</td>
<td>4.5V</td>
<td>50pF</td>
<td>9</td>
<td>17</td>
</tr>
<tr>
<td>참고</td>
<td>5.0V</td>
<td>15pF</td>
<td>7</td>
<td>-</td>
</tr>
<tr>
<td>규격</td>
<td>6.0V</td>
<td>50pF</td>
<td>7</td>
<td>14</td>
</tr>
	</table>
상승·하강 두 행의 1단 환산값을 같은 표에 견준다. 이 회로의 전원은 5V이고 부하는 U2 게이트 입력 하나와 프로브뿐이라 어느 규격 행과도 조건이 같지 않으므로, 한 숫자로 맞비교하기보다 조건을 나란히 적고 어느 쪽에 놓이는지를 본다.
<empty-block/>
<empty-block/>
# 회로 결선도
## 공통 결선 규칙
- 두 IC 모두 14번 핀을 +5V에, 7번 핀을 GND에 연결한다.
- 쓰지 않는 입력 핀은 강의노트 주의사항대로 VCC 또는 GND에 묶는다. 강의노트 그림을 따라 3·5번 핀은 GND로, 9·11·13번 핀은 VCC로 묶고 하나도 띄워 두지 않는다.
- 쓰지 않는 출력 핀은 아무 데도 연결하지 않고 개방한다.
- GND는 한 점이다. 전원 장치의 -, 함수발생기의 -, CH1·CH2 프로브의 접지 클립, IC 7번 핀을 모두 같은 GND 레일에 묶는다. 회로도에 접지 기호가 여러 개 그려져 있지만 전부 같은 GND다.
- 세 회로는 브레드보드의 같은 자리를 쓴다. 신호원 입력은 첫 칩의 1번 핀, 전원은 14번·7번 핀으로 회로가 바뀌어도 그대로다. 실험 1-2는 칩만 갈아 끼우고, 실험 2는 다시 74HC04로 갈아 끼운 뒤 미사용 입력 선 다섯 가닥을 걷고 체인 점퍼 다섯 가닥을 더한다. 그다음 두 번째 74HC04(U2)를 옆에 꽂아 14번·7번 핀에 전원을 걸고 미사용 입력 다섯 개를 VCC 또는 GND에 묶은 뒤, U1의 8번 핀을 U2의 1번 핀에 잇는다. 칩을 뽑고 꽂을 때는 전원을 끈다.
<empty-block/>
## 실험 1-1) Inverter의 입출력 특성 확인 결선
![실험 1-1) Inverter의 입출력 특성 브레드보드 작도]()
<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
</tr>
<tr>
<td>74HC04</td>
<td>1</td>
<td>함수발생기 +, 그리고 CH1 프로브 (VIN)</td>
</tr>
<tr>
<td>74HC04</td>
<td>2</td>
<td>CH2 프로브 (VOUT)</td>
</tr>
<tr>
<td>74HC04</td>
<td>3, 5</td>
<td>GND</td>
</tr>
<tr>
<td>74HC04</td>
<td>9, 11, 13</td>
<td>+5V</td>
</tr>
<tr>
<td>74HC04</td>
<td>4, 6, 8, 10, 12</td>
<td>개방</td>
</tr>
</table>
<empty-block/>
## 실험 1-2) Schmitt-trigger의 입출력 특성 확인 결선
![실험 1-2) Schmitt-trigger의 입출력 특성 브레드보드 작도]()
<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
</tr>
<tr>
<td>74HC14</td>
<td>1</td>
<td>함수발생기 +, 그리고 CH1 프로브 (VIN)</td>
</tr>
<tr>
<td>74HC14</td>
<td>2</td>
<td>CH2 프로브 (VOUT)</td>
</tr>
<tr>
<td>74HC14</td>
<td>3, 5</td>
<td>GND</td>
</tr>
<tr>
<td>74HC14</td>
<td>9, 11, 13</td>
<td>+5V</td>
</tr>
<tr>
<td>74HC14</td>
<td>4, 6, 8, 10, 12</td>
<td>개방</td>
</tr>
</table>
<empty-block/>
## 실험 2) CMOS의 AC 특성 확인 결선
![실험 2) CMOS의 AC 특성 브레드보드 작도]()
<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
</tr>
<tr>
<td>74HC04 (U1)</td>
<td>1</td>
<td>함수발생기 + (VIN)</td>
</tr>
<tr>
<td>74HC04 (U1)</td>
<td>2</td>
<td>같은 칩 3번 핀</td>
</tr>
<tr>
<td>74HC04 (U1)</td>
<td>4</td>
<td>같은 칩 5번 핀, 그리고 CH1 프로브</td>
</tr>
<tr>
<td>74HC04 (U1)</td>
<td>6</td>
<td>같은 칩 13번 핀</td>
</tr>
<tr>
<td>74HC04 (U1)</td>
<td>12</td>
<td>같은 칩 11번 핀</td>
</tr>
<tr>
<td>74HC04 (U1)</td>
<td>10</td>
<td>같은 칩 9번 핀</td>
</tr>
<tr>
<td>74HC04 (U1)</td>
<td>8</td>
<td>U2의 1번 핀, 그리고 CH2 프로브</td>
</tr>
<tr>
<td>74HC04 (U2)</td>
<td>1</td>
<td>U1의 8번 핀</td>
</tr>
<tr>
<td>74HC04 (U2)</td>
<td>3, 5</td>
<td>GND</td>
</tr>
<tr>
<td>74HC04 (U2)</td>
<td>9, 11, 13</td>
<td>+5V</td>
</tr>
<tr>
<td>74HC04 (U2)</td>
<td>2, 4, 6, 8, 10, 12</td>
<td>개방</td>
</tr>
</table>
<empty-block/>
## 실험 전 확인할 사항
- 함수발생기를 회로에 물린 뒤 CH1로 Vin이 실제로 Vpp 5V인지 먼저 본다. 출력 임피던스 설정(50Ω 또는 High-Z)에 따라 표시값과 실제 진폭이 다를 수 있다.
- 실험 2의 사각파는 강의노트가 offset을 적지 않았다. Vin이 0\~5V를 오가도록 offset 2.5V를 두고 CH1로 확인한다. offset 없이 넣으면 입력이 GND 아래로 내려간다.
- 실험 2에서 CH1(4번 핀)과 CH2(8번 핀) 사이의 단 수는 브레드보드의 체인 점퍼로 센다. 점퍼 다섯 가닥 중 두 프로브 사이에 놓인 것은 4번에서 5번, 6번에서 13번, 12번에서 11번, 10번에서 9번 네 가닥이므로 4단이다. 측정값에서 거꾸로 정하지 않는다.
- 오른쪽 열의 세 게이트는 입력 번호가 출력보다 크다. 체인 점퍼를 6번에서 13번, 12번에서 11번, 10번에서 9번으로 꽂았는지 방향을 다시 센다.
- 지급된 칩의 각인을 확인한다. 제조사가 Nexperia가 아니면 비교할 데이터시트를 그 제조사 것으로 바꾼다.
- 실험실 오실로스코프에서 X-Y 모드로 들어가는 경로와 CH1이 가로축인지 확인한다. 강의노트는 Horiz 메뉴의 좌측 아래 버튼이라고 안내한다.
<empty-block/>
<empty-block/>
# 출처 및 참고문헌
- 논리회로실험 강의노트
- 논리회로실험 IC 특성 분석 가이드
- Nexperia. 74HC04; 74HCT04 — Hex inverter. Rev. 10, 2024-02-16.
	[https://assets.nexperia.com/documents/data-sheet/74HC_HCT04.pdf](https://assets.nexperia.com/documents/data-sheet/74HC_HCT04.pdf)
- Nexperia. 74HC14; 74HCT14 — Hex inverting Schmitt trigger. Rev. 10, 2024-02-29.
	[https://assets.nexperia.com/documents/data-sheet/74HC_HCT14.pdf](https://assets.nexperia.com/documents/data-sheet/74HC_HCT14.pdf)