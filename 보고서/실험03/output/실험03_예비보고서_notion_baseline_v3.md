<table_of_contents color="gray"/>
<empty-block/>
# 실험 목적
가산기와 감산기가 무엇인지 이해하고, 논리 게이트만으로 그 회로를 직접 구성하는 것이 이번 실험의 목적이다. 강의노트는 목표를 가산기(Adder)와 감산기(Subtractor)의 이해, 그리고 논리 게이트 기반의 가산기·감산기 회로 구성 두 가지로 든다.
실험은 74HC86의 XOR 두 개로 합 S를 먼저 만들고, 74HC08의 AND 두 개와 74HC32의 OR로 올림 Co를 더해 전가산기를 완성하는 데서 시작한다. 이어 A가 들어가던 AND 입력과 A⊕B가 들어가던 AND 입력 앞에 74HC04 인버터를 하나씩 끼워 전감산기로 바꾼다. 두 회로 모두 출력에 발광다이오드를 달고 입력에 5V와 GND를 번갈아 넣어 가며 강의노트의 진리표와 맞는지 확인한다.
<empty-block/>
<empty-block/>
# 실험 이론
## 가산기와 감산기
가산기는 이진수 덧셈을, 감산기는 이진수 뺄셈을 수행하는 디지털 회로다. 강의노트는 이 둘을 CPU 안에서 연산을 맡는 ALU(Arithmetic Logic Unit)의 핵심 기능으로 소개한다. 가산기는 합과 올림 수(Carry)를, 감산기는 차와 내림 수(Borrow)를 출력한다.
1비트 덧셈은 네 경우뿐이다. 0+0=0, 0+1=1, 1+0=1이고, 1+1은 이진수로 10이라 합 자리는 0이 되고 윗자리로 1이 올라간다. 합 자리와 올림 자리를 따로 출력하면 그것이 반가산기이고, 아랫자리에서 올라온 올림까지 받아 세 비트를 더하면 전가산기다. 뺄셈도 같은 구조다. 0에서 1을 빼려면 윗자리에서 1을 빌려 와야 하므로 차 1과 내림 1을 낸다. 두 비트만 다루면 반감산기, 아랫자리가 빌려 간 내림까지 받으면 전감산기다.
<empty-block/>
## 기본 게이트
이번 실험 회로에 들어가는 게이트는 XOR·AND·OR·NOT 네 가지이고, 각각 74HC86·74HC08·74HC32·74HC04에 들어 있다. 강의노트에는 게이트별 진리표가 없어 아래 표는 제조사 데이터시트의 function table을 옮긴 것이다. 데이터시트는 H와 L로 적는데 이 실험은 H를 1, L을 0으로 읽는 양논리를 쓰므로 0과 1로 바꿔 적었다.
- **XOR** (Y = A⊕B)
	<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>Y</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
	</table>
- **AND** (Y = A·B)
	<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>Y</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
- **OR** (Y = A+B)
	<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>Y</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
- **NOT** (Y = A')
	<table header-row="true">
<tr>
<td>A</td>
<td>Y</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
</tr>
	</table>
XOR은 두 입력이 다를 때만 1이라 1비트 덧셈과 뺄셈의 합·차 자리를 그대로 만든다. 가산기와 감산기의 차이는 올림과 내림을 만드는 AND 쪽에만 있고, 그 자리에 인버터가 들어가느냐가 갈림이다.
<empty-block/>
## 반가산기
입력 A, B 두 비트를 받아 합 S와 올림 수 C를 낸다. 합 자리는 두 입력이 다를 때만 1이므로 XOR이고, 올림은 둘 다 1일 때만 생기므로 AND다.
- S = A⊕B
- C = A·B
앞선 자리에서 올라오는 올림을 받을 입력이 없어 가장 낮은 자리의 덧셈에만 쓴다. 전가산기는 이 반가산기 두 개로 짠다.
<empty-block/>
## 전가산기
입력 A, B에 아랫자리에서 올라온 올림 Ci까지 세 비트를 받아 합 S와 올림 Co를 낸다. 강의노트는 반가산기 두 개와 OR 게이트 하나로 구성한다. 첫 반가산기가 A와 B를 더해 A⊕B와 A·B를 만들고, 두 번째 반가산기가 그 합 A⊕B와 Ci를 더한다. 두 반가산기의 올림을 OR로 모은 것이 Co다.
- S = A⊕B⊕Ci
- Co = A·B + (A⊕B)·Ci
세 비트의 합 자리는 1의 개수가 홀수일 때 1이고, XOR을 두 번 거치면 그 값이 나온다. 올림은 A와 B가 둘 다 1이거나, 둘 중 하나만 1인 상태에서 Ci가 1일 때 생긴다. 두 올림이 동시에 1이 되는 경우는 없다. A·B가 1이면 A⊕B가 0이라 (A⊕B)·Ci도 0이기 때문이다. 그래서 두 올림을 합치는 자리에 OR 게이트 하나면 충분하다.
<empty-block/>
## 반감산기
입력 A에서 B를 빼 차 D와 내림 수 B를 낸다. 강의노트는 내림 수를 입력과 같은 글자 B로 적고, 이 보고서도 그 표기를 그대로 따른다. 아래 식의 왼쪽 B가 출력인 내림 수이고 오른쪽 B가 입력이다. 차 자리는 덧셈과 마찬가지로 두 입력이 다를 때만 1이라 XOR이고, 내림은 A가 0이고 B가 1일 때만 생긴다.
- D = A⊕B
- B = A'·B
반가산기와 견주면 XOR 쪽은 같고 AND 쪽만 다르다. 올림은 A·B인데 내림은 A'·B라, A를 인버터로 한 번 뒤집어 AND에 넣으면 된다. 인버터의 입력은 A 쪽이어야 하고, B 쪽이면 A·B'가 되어 A가 0이고 B가 1인 행이 어긋난다.
<empty-block/>
## 전감산기
입력 A, B에 아랫자리가 빌려 간 내림 Bi까지 받아 차 D와 내림 Bo를 낸다. 전가산기와 같은 꼴로 반감산기 두 개와 OR 게이트 하나로 구성한다. 첫 반감산기가 A에서 B를 빼 A⊕B와 A'·B를 만들고, 두 번째 반감산기가 그 차 A⊕B에서 Bi를 뺀다. 두 번째 반감산기의 내림은 (A⊕B)'·Bi라 여기에도 인버터가 하나 더 든다. 두 내림을 OR로 모은 것이 Bo다.
- D = A⊕B⊕Bi
- Bo = A'·B + (A⊕B)'·Bi
여기서도 두 내림은 동시에 1이 되지 않는다. A'·B가 1이면 A⊕B가 1이라 (A⊕B)'·Bi는 0이다. 그래서 전가산기와 같이 OR 게이트 하나로 합친다. 이 회로는 네 종류 칩을 전부 쓴다.
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
<td>모든 IC의 전원 핀과 입력에 공급</td>
</tr>
<tr>
<td>74HC86</td>
<td>quad 2-input XOR, DIP-14</td>
<td>1</td>
<td>두 회로 모두 게이트 두 개를 쓴다</td>
</tr>
<tr>
<td>74HC08</td>
<td>quad 2-input AND, DIP-14</td>
<td>1</td>
<td>두 회로 모두 게이트 두 개를 쓴다</td>
</tr>
<tr>
<td>74HC32</td>
<td>quad 2-input OR, DIP-14</td>
<td>1</td>
<td>전가산기·전감산기의 올림·내림 합류</td>
</tr>
<tr>
<td>74HC04</td>
<td>hex inverter, DIP-14</td>
<td>1</td>
<td>전감산기. 인버터 두 개를 한 칩에서 쓴다</td>
</tr>
<tr>
<td>발광다이오드</td>
<td></td>
<td>2</td>
<td>합·차 출력과 올림·내림 출력</td>
</tr>
<tr>
<td>저항</td>
<td>330Ω</td>
<td>2</td>
<td>발광다이오드 애노드에 직렬로 넣는다</td>
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
<td>입력을 +5V·GND에 물리고 게이트 사이를 잇는다</td>
</tr>
</table>
같은 종류의 게이트를 가장 많이 쓰는 것이 전감산기의 XOR·AND·NOT 두 개씩이라, IC는 종류당 한 칩이면 된다.
<empty-block/>
## 핀 배치
<table header-row="true">
<tr>
<td>IC</td>
<td>게이트1</td>
<td>게이트2</td>
<td>게이트3</td>
<td>게이트4</td>
<td>VCC</td>
<td>GND</td>
</tr>
<tr>
<td>74HC86 (quad XOR)</td>
<td>1,2 → 3</td>
<td>4,5 → 6</td>
<td>9,10 → 8</td>
<td>12,13 → 11</td>
<td>14</td>
<td>7</td>
</tr>
<tr>
<td>74HC08 (quad AND)</td>
<td>1,2 → 3</td>
<td>4,5 → 6</td>
<td>9,10 → 8</td>
<td>12,13 → 11</td>
<td>14</td>
<td>7</td>
</tr>
<tr>
<td>74HC32 (quad OR)</td>
<td>1,2 → 3</td>
<td>4,5 → 6</td>
<td>9,10 → 8</td>
<td>12,13 → 11</td>
<td>14</td>
<td>7</td>
</tr>
</table>
74HC04는 인버터 6개짜리라 배치가 다르다. 1→2, 3→4, 5→6, 9→8, 11→10, 13→12이고 VCC는 14번, GND는 7번이다.
강의노트 회로도에는 게이트 기호와 IC 이름만 있고 핀 번호가 없어, 위 배치는 네 IC의 제조사 데이터시트에서 옮겼다. 쿼드 게이트 세 칩은 핀 배치가 전부 같아서 게이트 하나를 어느 칩에서 뽑든 같은 번호로 센다. 이번 실험에서 74HC04는 앞쪽 인버터 두 개(1→2, 3→4)만 쓴다.
<empty-block/>
<empty-block/>
# 실험 과정 및 예상 결과
## 실험 1-2) 전가산기
74HC86의 첫 번째 XOR에 입력 A와 B를 넣고, 그 출력 A⊕B를 두 번째 XOR에 Ci와 함께 넣어 합 S를 만든다. 74HC08의 첫 번째 AND에는 A와 B를, 두 번째 AND에는 A⊕B와 Ci를 넣고, 두 AND 출력을 74HC32의 OR에 모은 것이 올림 Co다. 두 출력에 각각 330Ω 저항과 발광다이오드를 단다. XOR 쪽을 먼저 꽂아 S만 여덟 조합으로 본 뒤, AND와 OR을 더해 Co까지 본다. S는 입력에 1이 홀수 개일 때, Co는 1이 둘 이상일 때 켜져야 한다.
- **전가산기** (S = A⊕B⊕Ci, Co = A·B + (A⊕B)·Ci)
	<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>Ci</td>
<td>S</td>
<td>Co</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
<empty-block/>
## 실험 2-2) 전감산기
전가산기 회로에서 두 곳만 바꾼다. 첫 번째 AND로 가던 A를 74HC04의 첫 번째 인버터를 거친 A'로 바꾸고, 두 번째 AND로 가던 A⊕B를 두 번째 인버터를 거친 (A⊕B)'로 바꾼다. Ci 자리에 넣던 입력은 그대로 Bi가 되고, 두 발광다이오드도 그 자리에 둔다. 두 번째 XOR 출력이 차 D, OR 출력이 내림 Bo다. 여덟 조합에서 D는 입력에 1이 홀수 개일 때 켜지고, Bo는 A가 0이면서 B와 Bi 중 하나라도 1일 때와 세 입력이 모두 1일 때 켜져야 한다.
- **전감산기** (D = A⊕B⊕Bi, Bo = A'·B + (A⊕B)'·Bi)
	<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>Bi</td>
<td>D</td>
<td>Bo</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
<empty-block/>
<empty-block/>
# 회로 결선도
## 공통 결선 규칙
- 네 IC 모두 14번 핀을 +5V에, 7번 핀을 GND에 연결한다.
- 쓰는 게이트의 입력은 반드시 어딘가에 물린다. 쓰지 않는 게이트의 입력은 강의노트가 처리를 따로 지시하지 않아 개방해 두는데, 실험1에서 접지를 생략해도 결과에 영향이 없었다. 쓰지 않는 출력 핀은 아무 데도 연결하지 않는다. 출력끼리 묶거나 GND로 내리면 정격을 넘는 전류가 흐른다.
- 입력 A·B·Ci·Bi는 점퍼선으로 +5V(=1) 또는 GND(=0)에 직접 물린다. 띄워 두지 않는다.
- 발광다이오드는 두 개다. LED1은 합·차(S·D), LED2는 올림·내림(Co·Bo) 자리다. 애노드 쪽에 330Ω 저항을 직렬로 넣고 캐소드를 GND로 내린다. 두 회로에서 급전선 자리도 같다(S와 D는 74HC86 6번 핀, Co와 Bo는 74HC32 3번 핀).
- 두 회로는 브레드보드의 같은 자리를 쓴다. 74HC86은 왼쪽 블록 위, 74HC04는 그 아래, 74HC08과 74HC32는 오른쪽 블록에 두고, 회로가 바뀌어도 칩과 전원선, 입력 A·B의 갈래는 그대로 둔다. 같은 종류 칩이 두 번 그려진 회로도는 한 칩의 두 번째 게이트를 쓰는 것이다.
- 칩을 꽂거나 뽑을 때는 전원을 끈다. 전가산기에서 전감산기로 넘어갈 때 걷는 선은 두 가닥뿐이다. 입력 A에서 74HC08 1번 핀으로 가던 선과, 74HC86 3번 핀에서 74HC08 4번 핀으로 가던 선이다.
<empty-block/>
## 실험 1-2) 전가산기 결선
![실험 1-2) 전가산기 브레드보드 작도]()
<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
</tr>
<tr>
<td>74HC86</td>
<td>1</td>
<td>입력 A</td>
</tr>
<tr>
<td>74HC86</td>
<td>2</td>
<td>입력 B</td>
</tr>
<tr>
<td>74HC86</td>
<td>3</td>
<td>같은 칩 4번 핀, 그리고 74HC08의 4번 핀 (A⊕B)</td>
</tr>
<tr>
<td>74HC86</td>
<td>4</td>
<td>같은 칩 3번 핀</td>
</tr>
<tr>
<td>74HC86</td>
<td>5</td>
<td>입력 Ci</td>
</tr>
<tr>
<td>74HC86</td>
<td>6</td>
<td>LED1 (S)</td>
</tr>
<tr>
<td>74HC86</td>
<td>8, 9, 10, 11, 12, 13</td>
<td>개방</td>
</tr>
<tr>
<td>74HC08</td>
<td>1</td>
<td>입력 A</td>
</tr>
<tr>
<td>74HC08</td>
<td>2</td>
<td>입력 B</td>
</tr>
<tr>
<td>74HC08</td>
<td>3</td>
<td>74HC32의 2번 핀 (A·B)</td>
</tr>
<tr>
<td>74HC08</td>
<td>4</td>
<td>74HC86의 3번 핀</td>
</tr>
<tr>
<td>74HC08</td>
<td>5</td>
<td>입력 Ci</td>
</tr>
<tr>
<td>74HC08</td>
<td>6</td>
<td>74HC32의 1번 핀 ((A⊕B)·Ci)</td>
</tr>
<tr>
<td>74HC08</td>
<td>8, 9, 10, 11, 12, 13</td>
<td>개방</td>
</tr>
<tr>
<td>74HC32</td>
<td>1</td>
<td>74HC08의 6번 핀</td>
</tr>
<tr>
<td>74HC32</td>
<td>2</td>
<td>74HC08의 3번 핀</td>
</tr>
<tr>
<td>74HC32</td>
<td>3</td>
<td>LED2 (Co)</td>
</tr>
<tr>
<td>74HC32</td>
<td>4, 5, 6, 8, 9, 10, 11, 12, 13</td>
<td>개방</td>
</tr>
</table>
<empty-block/>
## 실험 2-2) 전감산기 결선
![실험 2-2) 전감산기 브레드보드 작도]()
<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
</tr>
<tr>
<td>74HC86</td>
<td>1</td>
<td>입력 A</td>
</tr>
<tr>
<td>74HC86</td>
<td>2</td>
<td>입력 B</td>
</tr>
<tr>
<td>74HC86</td>
<td>3</td>
<td>같은 칩 4번 핀, 그리고 74HC04의 3번 핀 (A⊕B)</td>
</tr>
<tr>
<td>74HC86</td>
<td>4</td>
<td>같은 칩 3번 핀</td>
</tr>
<tr>
<td>74HC86</td>
<td>5</td>
<td>입력 Bi</td>
</tr>
<tr>
<td>74HC86</td>
<td>6</td>
<td>LED1 (D)</td>
</tr>
<tr>
<td>74HC86</td>
<td>8, 9, 10, 11, 12, 13</td>
<td>개방</td>
</tr>
<tr>
<td>74HC04</td>
<td>1</td>
<td>입력 A</td>
</tr>
<tr>
<td>74HC04</td>
<td>2</td>
<td>74HC08의 1번 핀 (A')</td>
</tr>
<tr>
<td>74HC04</td>
<td>3</td>
<td>74HC86의 3번 핀</td>
</tr>
<tr>
<td>74HC04</td>
<td>4</td>
<td>74HC08의 4번 핀 ((A⊕B)')</td>
</tr>
<tr>
<td>74HC04</td>
<td>5, 6, 8, 9, 10, 11, 12, 13</td>
<td>개방</td>
</tr>
<tr>
<td>74HC08</td>
<td>1</td>
<td>74HC04의 2번 핀</td>
</tr>
<tr>
<td>74HC08</td>
<td>2</td>
<td>입력 B</td>
</tr>
<tr>
<td>74HC08</td>
<td>3</td>
<td>74HC32의 2번 핀 (A'·B)</td>
</tr>
<tr>
<td>74HC08</td>
<td>4</td>
<td>74HC04의 4번 핀</td>
</tr>
<tr>
<td>74HC08</td>
<td>5</td>
<td>입력 Bi</td>
</tr>
<tr>
<td>74HC08</td>
<td>6</td>
<td>74HC32의 1번 핀 ((A⊕B)'·Bi)</td>
</tr>
<tr>
<td>74HC08</td>
<td>8, 9, 10, 11, 12, 13</td>
<td>개방</td>
</tr>
<tr>
<td>74HC32</td>
<td>1</td>
<td>74HC08의 6번 핀</td>
</tr>
<tr>
<td>74HC32</td>
<td>2</td>
<td>74HC08의 3번 핀</td>
</tr>
<tr>
<td>74HC32</td>
<td>3</td>
<td>LED2 (Bo)</td>
</tr>
<tr>
<td>74HC32</td>
<td>4, 5, 6, 8, 9, 10, 11, 12, 13</td>
<td>개방</td>
</tr>
</table>
<empty-block/>
## 실험 전 확인할 사항
- 지급된 IC가 종류당 한 개인지 본다. 두 회로를 한 벌의 칩으로 순서대로 배선하는 것을 전제로 그렸다.
- 칩의 각인을 확인한다. 74HC 계열이면 제조사가 달라도 핀 배치는 같지만, 74HCT나 74LS면 전기 특성이 달라 비교할 데이터시트를 바꾼다.
- 오른쪽 블록은 전원 레일이 왼쪽과 좌우로 뒤집혀 있다. 74HC08과 74HC32의 7번 핀은 가운데 GND 레일로, 14번 핀은 바깥쪽 +5V 레일로 간다. 그림대로 꽂았는지 전원을 넣기 전에 다시 본다.
- 전감산기에서 첫 번째 인버터에 들어가는 것이 A이고 B가 아닌지 확인한다. 바뀌면 A·B'가 되어 A가 0이고 B가 1인 행에서 Bo가 틀린다.
- 330Ω을 달았을 때 발광다이오드 전류는 대략 9mA다. 강의노트 지시대로 게이트 출력으로 직접 구동하되 LED가 눈에 띄게 어두우면 이 지점을 먼저 본다.
- 강의노트가 입력 스위치를 지정하지 않아 점퍼선을 +5V·GND에 직접 물린다. 조교가 미사용 입력의 접지나 풀업을 지시하면 그대로 따른다.
<empty-block/>
<empty-block/>
# 출처 및 참고문헌
- 논리회로실험 강의노트
- 논리회로실험 IC 특성 분석 가이드
- Nexperia. 74HC04; 74HCT04 — Hex inverter. Rev. 10, 2024-02-16.
	[https://assets.nexperia.com/documents/data-sheet/74HC_HCT04.pdf](https://assets.nexperia.com/documents/data-sheet/74HC_HCT04.pdf)
- Nexperia. 74HC08; 74HCT08 — Quad 2-input AND gate. Rev. 9, 2024-02-16.
	[https://assets.nexperia.com/documents/data-sheet/74HC_HCT08.pdf](https://assets.nexperia.com/documents/data-sheet/74HC_HCT08.pdf)
- Nexperia. 74HC32; 74HCT32 — Quad 2-input OR gate. Rev. 10, 2025-04-30.
	[https://assets.nexperia.com/documents/data-sheet/74HC_HCT32.pdf](https://assets.nexperia.com/documents/data-sheet/74HC_HCT32.pdf)
- Nexperia. 74HC86; 74HCT86 — Quad 2-input EXCLUSIVE-OR gate. Rev. 7, 2024-04-02.
	[https://assets.nexperia.com/documents/data-sheet/74HC_HCT86.pdf](https://assets.nexperia.com/documents/data-sheet/74HC_HCT86.pdf)