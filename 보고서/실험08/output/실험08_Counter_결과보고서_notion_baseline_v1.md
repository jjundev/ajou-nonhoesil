<table_of_contents color="gray"/>
<empty-block/>
# 실험 결과
## 실험 1) 2단 2진 카운터 (비동기)
74HC76의 JK 플립플롭 두 개를 J=K=1로 두어 Toggle하게 하고, FFA의 출력 A를 FFB의 클럭으로 넣은 비동기 카운터다. 74HC08의 AND 게이트 네 개로 Y0=A'·B', Y1=A·B', Y2=A'·B, Y3=A·B를 만들어 각 출력에 LED를 달았다. 클럭은 오실로스코프로 0\~5V, 주기 약 1s의 사각파임을 확인한 뒤 넣었고, 표의 RUN은 클럭을 계속 넣은 상태를 뜻한다.
- **2단 2진 카운터 출력 순서**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>CLK</td>
<td>Y0</td>
<td>Y1</td>
<td>Y2</td>
<td>Y3</td>
</tr>
<tr>
<td>S1</td>
<td>AB=00 구간. Y0이 켜진 때를 기준으로 잡는다</td>
<td>RUN</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S2</td>
<td>AB=10 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S3</td>
<td>AB=01 구간</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>S4</td>
<td>AB=11 구간</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>S5</td>
<td>AB=00 구간으로 복귀</td>
<td>RUN</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
다섯 스텝 모두 예상과 일치했다. 네 LED는 약 1s 간격으로 Y0, Y1, Y2, Y3 순서로 하나씩만 켜졌고, Y3 다음에는 다시 Y0이 켜지는 순환이 두 바퀴 넘게 이어졌다. 전원을 넣은 직후 어느 LED부터 켜지는지는 정해져 있지 않았는데, 촬영을 시작한 순간에는 Y3이 켜져 있었고 그 다음부터 Y0으로 넘어가 순서대로 돌았다.
<empty-block/>
## 실험 3) 7-Segment 표시기를 갖는 BCD 카운터
7490의 INPUT A에 클럭을 넣고 QA를 INPUT B로 되돌린 BCD 카운터, Common Anode 표시기 FND 507, 그리고 BCD 입력을 세그먼트 신호 a\~g로 바꾸는 7447을 차례로 구성한 뒤 하나로 연결했다. R9 두 핀은 GND에 잇고 R0 두 핀은 묶어서 점퍼로 +5V 또는 GND에 꽂았다. 카운터 단계의 A\~D는 7490의 출력 QA\~QD에 단 LED이고, 표시기 단계의 D, C, B, A는 7447의 입력이다.
- **BCD Counter 출력**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>CLK</td>
<td>R0</td>
<td>A</td>
<td>B</td>
<td>C</td>
<td>D</td>
</tr>
<tr>
<td>R1</td>
<td>R0 점퍼를 +5V에 꽂고 클럭을 넣는다</td>
<td>RUN</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>N1</td>
<td>R0 점퍼를 GND로 옮긴 뒤 COUNT 1 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>N2</td>
<td>COUNT 2 구간</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>N3</td>
<td>COUNT 3 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>N4</td>
<td>COUNT 4 구간</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>N5</td>
<td>COUNT 5 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>N6</td>
<td>COUNT 6 구간</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>N7</td>
<td>COUNT 7 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>N8</td>
<td>COUNT 8 구간</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>N9</td>
<td>COUNT 9 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>N0</td>
<td>COUNT 0으로 복귀</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
R0을 +5V에 꽂아 둔 동안에는 클럭이 계속 들어가도 네 LED가 모두 꺼진 채 0을 유지했다. R0을 GND로 옮기자 약 1s마다 한 칸씩 세어 나갔고, A\~D LED의 점등은 0부터 9까지 모두 예상과 일치했다. 9 다음에는 A와 D가 함께 꺼지면서 0으로 돌아갔다.
- **FND 507 Common Anode 테스트**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>FND 핀</td>
<td>예상 세그먼트</td>
<td>실제 세그먼트</td>
</tr>
<tr>
<td>F1</td>
<td>pin 7의 330Ω 끝을 GND에 댄다</td>
<td>7</td>
<td>Segment A</td>
<td>Segment A</td>
</tr>
<tr>
<td>F2</td>
<td>pin 6의 330Ω 끝을 GND에 댄다</td>
<td>6</td>
<td>Segment B</td>
<td>Segment B</td>
</tr>
<tr>
<td>F3</td>
<td>pin 4의 330Ω 끝을 GND에 댄다</td>
<td>4</td>
<td>Segment C</td>
<td>Segment C</td>
</tr>
<tr>
<td>F4</td>
<td>pin 2의 330Ω 끝을 GND에 댄다</td>
<td>2</td>
<td>Segment D</td>
<td>Segment D</td>
</tr>
<tr>
<td>F5</td>
<td>pin 1의 330Ω 끝을 GND에 댄다</td>
<td>1</td>
<td>Segment E</td>
<td>Segment E</td>
</tr>
<tr>
<td>F6</td>
<td>pin 9의 330Ω 끝을 GND에 댄다</td>
<td>9</td>
<td>Segment F</td>
<td>Segment F</td>
</tr>
<tr>
<td>F7</td>
<td>pin 10의 330Ω 끝을 GND에 댄다</td>
<td>10</td>
<td>Segment G</td>
<td>Segment G</td>
</tr>
	</table>
3번과 8번에 +5V를 준 상태에서 세그먼트 핀을 하나씩 GND 쪽으로 당기자 핀표의 세그먼트가 하나씩 켜져, 받은 FND가 Common Anode이고 핀 배치도 핀표와 같다는 것을 확인했다.
- **BCD to 7-Segment 입출력**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>D</td>
<td>C</td>
<td>B</td>
<td>A</td>
<td>켜지는 세그먼트</td>
<td>예상 숫자</td>
<td>실제 숫자</td>
</tr>
<tr>
<td>I0</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>abcdef</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>I1</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>bc</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>I2</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>abdeg</td>
<td>2</td>
<td>2</td>
</tr>
<tr>
<td>I3</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>abcdg</td>
<td>3</td>
<td>3</td>
</tr>
<tr>
<td>I4</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>bcfg</td>
<td>4</td>
<td>4</td>
</tr>
<tr>
<td>I5</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>acdfg</td>
<td>5</td>
<td>5</td>
</tr>
<tr>
<td>I6</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>cdefg</td>
<td>6</td>
<td>6</td>
</tr>
<tr>
<td>I7</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>abc</td>
<td>7</td>
<td>7</td>
</tr>
<tr>
<td>I8</td>
<td>입력 점퍼를 표대로 옮긴다</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>abcdefg</td>
<td>8</td>
<td>8</td>
</tr>
<tr>
<td>I9</td>
<td>입력 점퍼를 표대로 옮기고 d 세그먼트가 켜졌는지도 본다</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>abcfg</td>
<td>9</td>
<td>9(d 꺼짐)</td>
</tr>
	</table>
열 가지 입력 모두 해당하는 숫자가 표시됐다. 1001을 넣었을 때는 강의노트 표대로 d가 꺼진 9가 나왔다. 0110에서는 숫자 6이 표시된 것만 확인했고, 이때 맨 위 a 세그먼트가 켜졌는지는 따로 보지 않았다.
- **7-Segment 표시기를 갖는 BCD 카운터**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>CLK</td>
<td>R0</td>
<td>예상 숫자</td>
<td>실제 숫자</td>
</tr>
<tr>
<td>R1</td>
<td>최종 결선을 마친 뒤 R0 점퍼를 +5V에 꽂고 클럭을 넣는다</td>
<td>RUN</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>N1</td>
<td>R0 점퍼를 GND로 옮긴 뒤 COUNT 1 구간</td>
<td>RUN</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>N2</td>
<td>COUNT 2 구간</td>
<td>RUN</td>
<td>0</td>
<td>2</td>
<td>2</td>
</tr>
<tr>
<td>N3</td>
<td>COUNT 3 구간</td>
<td>RUN</td>
<td>0</td>
<td>3</td>
<td>3</td>
</tr>
<tr>
<td>N4</td>
<td>COUNT 4 구간</td>
<td>RUN</td>
<td>0</td>
<td>4</td>
<td>4</td>
</tr>
<tr>
<td>N5</td>
<td>COUNT 5 구간</td>
<td>RUN</td>
<td>0</td>
<td>5</td>
<td>5</td>
</tr>
<tr>
<td>N6</td>
<td>COUNT 6 구간</td>
<td>RUN</td>
<td>0</td>
<td>6</td>
<td>**6(a 켜짐)**</td>
</tr>
<tr>
<td>N7</td>
<td>COUNT 7 구간</td>
<td>RUN</td>
<td>0</td>
<td>7</td>
<td>7</td>
</tr>
<tr>
<td>N8</td>
<td>COUNT 8 구간</td>
<td>RUN</td>
<td>0</td>
<td>8</td>
<td>8</td>
</tr>
<tr>
<td>N9</td>
<td>COUNT 9 구간. d 세그먼트가 켜졌는지도 본다</td>
<td>RUN</td>
<td>0</td>
<td>9</td>
<td>9(d 꺼짐)</td>
</tr>
<tr>
<td>N0</td>
<td>COUNT 0으로 복귀</td>
<td>RUN</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
최종 회로에서도 R0=1 동안은 0이 유지됐고, R0을 내리자 FND가 약 1s마다 1부터 9까지 바뀐 뒤 0으로 돌아왔다. 9에서 0으로 넘어가는 장면은 한 번 촬영하는 동안 두 번 나왔다. 숫자는 모두 맞게 읽혔지만 6의 모양은 강의노트 표와 달랐다. 6은 a까지 켜진 꼬리 있는 모양이었다. 9는 정적 시험과 같이 d가 꺼진 모양으로, 강의노트 표와 같았다.
<empty-block/>
<empty-block/>
# 실험 사진
항목마다 예비보고서에서 그린 결선도를 먼저 싣고, 그 아래에 클럭을 넣은 채 촬영한 영상에서 상태별 장면을 골라 한 장에 모았다. 각 사진 위의 띠에는 그 장면의 카운터 상태와 켜진 LED를 적었다. 실험 3의 FND는 보드 위에 옆으로 눕혀 꽂혀 있어, 사진마다 FND 부분을 바로 세워 확대한 그림을 오른쪽 아래에 덧붙였다.
<empty-block/>
## 실험 1) 2단 2진 카운터 (비동기)
![예비보고서에서 그린 2단 2진 카운터 결선도](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/2424009e-6766-4a52-841d-8d274f0e5b82/%EC%8B%A4%ED%97%9808_1_%EC%86%90%EA%B7%B8%EB%A6%BC_2%EB%8B%A82%EC%A7%84%EC%B9%B4%EC%9A%B4%ED%84%B0.png)
![2단 2진 카운터의 네 상태와 Y0 복귀](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/a0d0e6d9-494f-4ea1-84e1-ad26b2621c87/%EC%8B%A4%ED%97%9808_1_%EC%82%AC%EC%A7%84_2%EB%8B%A82%EC%A7%84%EC%B9%B4%EC%9A%B4%ED%84%B0.jpg)
<empty-block/>
## 실험 3) 7-Segment 표시기를 갖는 BCD 카운터
![예비보고서에서 그린 7-Segment 표시기를 갖는 BCD 카운터 결선도](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/ad6194f7-0ce0-4f55-8c07-568834cc2b9e/%EC%8B%A4%ED%97%9808_3_%EC%86%90%EA%B7%B8%EB%A6%BC_BCD%ED%91%9C%EC%8B%9C%EA%B8%B0.png)
![최종 회로에서 0부터 9까지 표시된 숫자와 A\~D LED. 9에서 0으로 돌아온 직후부터 한 바퀴를 모았다](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/b0545fa7-6463-4807-8dc6-d7ffaf9873e6/%EC%8B%A4%ED%97%9808_3_%EC%82%AC%EC%A7%84_BCD%EC%B9%B4%EC%9A%B4%ED%84%B0.jpg)
<empty-block/>
<empty-block/>
# 예비보고서와의 비교
실험 1은 예비보고서의 예상대로 네 출력이 Y0, Y1, Y2, Y3 순서로 1s씩 하나만 켜지고 Y0으로 돌아왔다. 예비보고서에서 초기화 입력이 없어 시작 상태가 정해지지 않는다고 보고 Y0이 켜진 구간을 기준으로 잡기로 했는데, 실제로도 Y3이 켜진 상태에서 관찰이 시작되어 그 기준이 필요했다.
실험 3의 BCD Counter는 R0=1에서 0을 유지하고 R0=0에서 0부터 9까지 센 뒤 0으로 돌아오는 예상과 일치했다. FND 테스트에서는 세그먼트 일곱 개가 모두 핀표대로 켜져 Common Anode임을 확인한 뒤 다음 단계로 넘어갈 수 있었다.
차이는 표시 모양에서 나왔다. 예비보고서를 쓸 당시 강의노트 표는 9를 abcdfg로 적어 d를 포함했는데, 예비보고서는 SN7447A 동작표에서는 d가 꺼진다는 점을 짚고 실험에서 d의 상태를 보기로 했다. 이후 정정된 강의노트에서 9는 abcfg로 바뀌었고, 정적 시험과 최종 회로 모두 d가 꺼진 9가 나와 정정된 표와 일치했다. 반면 6은 강의노트 표와 SN7447A 동작표가 모두 a가 꺼진 cdefg인데, 최종 회로에서는 a가 켜진 6이 나왔다. 이 차이는 예비보고서에서 예상하지 못한 부분이다.
<empty-block/>
<empty-block/>
# 결과 분석
실험 1의 두 플립플롭은 J=K=1이라 하강 에지마다 출력을 뒤집는다. FFA는 클럭의 하강 에지마다, FFB는 A가 1에서 0으로 떨어질 때마다 바뀐다. 영상에서 LED가 약 1s마다 다음 것으로 넘어갔으므로 A는 1s 켜지고 1s 꺼지는 2s 주기, B는 2s씩 켜지고 꺼지는 4s 주기였고, 네 상태를 한 바퀴 도는 데 4s가 걸렸다. 클럭 주기 1s의 2배와 4배이므로 A는 클럭의 2분주, B는 4분주다.
74HC08에 넣을 A'와 B'는 인버터를 따로 쓰지 않고 74HC76의 Q' 출력인 14번과 10번에서 받았다. AND 게이트 네 개는 A, A', B, B' 중 둘씩을 받아 네 조합 중 하나에서만 1을 내므로 상태마다 LED가 정확히 하나만 켜졌다. LED가 Y0, Y1, Y2, Y3 순서로 켜졌다는 것은 AB가 00, 10, 01, 11 순서로 바뀌었다는 뜻이고, B를 높은 자리로 읽으면 0, 1, 2, 3으로 하나씩 올라가는 상향 카운터다. 클럭을 직접 받는 A가 가장 자주 바뀌므로 낮은 자리가 된다.
두 플립플롭의 PR과 CL이 모두 VCC에 묶여 있어 전원을 넣을 때의 AB를 정할 방법이 없고, 그래서 관찰을 Y3에서 시작하게 됐다. 네 상태가 모두 한 순환 안에 들어 있으므로 어느 상태에서 시작하든 3s 안에 Y0을 지나 같은 순서를 돈다.
7490은 INPUT A로 동작하는 2분주 단과 INPUT B로 동작하는 5분주 단으로 나뉜다. QA를 INPUT B에 연결했기 때문에 QA가 1에서 0으로 떨어질 때마다 뒷단이 한 칸 진행하고, 전체로는 2×5=10개의 상태를 돌아 9 다음 0이 된다. 9(QD=1, QA=1)에서 다음 에지가 오면 QA가 0으로 떨어지면서 뒷단이 4에서 0으로 돌아가므로 A와 D가 함께 꺼진 것이다.
이 구조 때문에 네 출력이 켜져 있는 시간은 서로 다르다. 숫자가 약 1s마다 바뀌었으므로 QA는 홀수에서만 켜지는 2s 주기, QC는 4부터 7까지 4s, QD는 8과 9에서만 켜져 10s 중 2s만 켜진다. QB는 2·3과 6·7에서 켜지고 8·9에서는 꺼져, 2진 카운터처럼 4s마다 같은 모양을 되풀이하지 않는다. 5분주 단이 4에서 곧바로 0으로 돌아가기 때문이다. 따라서 QD 하나를 보면 클럭의 10분주이지만 켜져 있는 비율은 20%로, 실험 1의 B가 4s 중 2s씩 켜져 있던 것과 다르다.
R9 두 핀을 GND에 고정하고 묶은 R0만 조작했으므로, R0=1이면 Reset 표의 첫 두 행에 해당해 클럭이 들어와도 출력이 0에 머물렀고 R0=0이면 카운트 행으로 넘어갔다.
표시기 쪽은 처음 배포된 강의노트 회로도의 FND 핀 번호가 강의노트 끝의 FND 507 핀표와 맞지 않았다. 이번 실험은 핀표대로 결선했고, 이후 조교 공지와 정정된 강의노트에서 같은 결선으로 바로잡혔다. 두 결선을 비교하면 다음과 같다.
- **정정 전 강의노트 회로도와 핀표에 따른 FND 결선 비교**
	<table header-row="true">
<tr>
<td>연결</td>
<td>7447 핀</td>
<td>정정 전 회로도의 FND 핀</td>
<td>핀표에 따른 FND 핀</td>
</tr>
<tr>
<td>a</td>
<td>13</td>
<td>7</td>
<td>7</td>
</tr>
<tr>
<td>b</td>
<td>12</td>
<td>6</td>
<td>6</td>
</tr>
<tr>
<td>c</td>
<td>11</td>
<td>4</td>
<td>4</td>
</tr>
<tr>
<td>d</td>
<td>10</td>
<td>3</td>
<td>2</td>
</tr>
<tr>
<td>e</td>
<td>9</td>
<td>2</td>
<td>1</td>
</tr>
<tr>
<td>f</td>
<td>15</td>
<td>9</td>
<td>9</td>
</tr>
<tr>
<td>g</td>
<td>14</td>
<td>10</td>
<td>10</td>
</tr>
<tr>
<td>+5V</td>
<td>없음</td>
<td>1, 5</td>
<td>3, 8</td>
</tr>
	</table>
회로도대로 꽂았다면 공통 Anode인 3번에는 d 출력이 가고 8번은 비므로, Anode 어디에도 +5V가 들어가지 않는다. 7447의 출력은 전류를 받아들이기만 하므로 어떤 세그먼트에도 전류가 흐를 수 없어 표시기는 전부 꺼졌을 것이다. 또 e 출력이 2번인 Segment D로 가므로 d 자리에 e 신호가 나타났을 것이다. 조교 공지도 회로도대로 연결하면 숫자가 정상적으로 표시되지 않는다고 안내했다. 실제로는 FND 테스트에서 일곱 세그먼트가 핀표대로 켜졌고, 이후 0부터 9까지 모든 숫자가 읽을 수 있는 모양으로 나와 결선에는 문제가 없었다고 본다.
9에서 d가 꺼진 것은 결선 문제가 아니라 디코더의 표시 방식이다. 입력 점퍼로 1001을 넣은 정적 시험과 7490 출력을 넣은 최종 회로에서 똑같이 d가 꺼졌으므로 카운터와는 관계가 없고, d 세그먼트는 0, 2, 3, 5, 6, 8에서 정상으로 켜졌다. SN7447A 동작표에서 입력 1001은 a, b, c, f, g만 켜고 d와 e는 끄며, 정정된 강의노트 표도 9를 abcfg로 적는다. 9는 예상과 같은 모양으로 나온 것이다.
6에서 a가 켜진 것도 결선으로는 설명되지 않는다. 최종 회로에서 6이 표시된 장면에는 7490 출력에 단 LED 중 B와 C가 켜져 있어, 7447에 들어간 입력은 예상대로 0110이었다. a 세그먼트는 a를 쓰는 0, 2, 3, 5, 7, 8, 9에서 켜지고 a를 쓰지 않는 1과 4에서 꺼졌으므로 a 출력에서 FND까지의 결선도 정상이다. 강의노트 표의 cdefg와 비교하면 다른 세그먼트는 a 하나뿐이므로, 7447이 입력 0110에서 a 출력을 0으로 내린 것이다. 따라서 이번에 쓴 디코더 칩이 6을 a까지 켜는 모양으로 만들어져 있었을 가능성이 높다. 조교 공지는 이 칩을 74HC47로 적었고, 강의노트 표와 SN7447A 동작표는 6과 9를 모두 꼬리 없이 표시한다. 같은 데이터시트는 6과 9를 모두 꼬리 있게 표시하는 계열을 따로 소개하는데, 이번 칩은 6만 꼬리가 있어 그 계열과도 다르다. 정적 시험에서는 6의 a 상태를 보지 않아 점퍼 입력과도 비교하지 못했으므로, 실제로 쓴 칩의 각인과 그 제조사 데이터시트의 표시 표를 확인해야 원인을 확정할 수 있다.
<empty-block/>
<empty-block/>
# 고찰
실험 목적은 2단 2진 카운터의 동작 확인, 7490 BCD 카운터 구성, 카운터 값의 숫자 표시였다. 2단 2진 카운터에서는 네 출력이 Y0부터 Y3까지 1s씩 하나만 켜지고 다시 Y0으로 돌아오는 것을 확인했다. BCD 카운터에서는 R0으로 0에 고정한 뒤 해제하자 A\~D LED가 0부터 9까지 BCD로 바뀌고 0으로 돌아왔고, 7447과 FND를 연결한 최종 회로에서도 0부터 9까지 모든 숫자가 읽을 수 있는 모양으로 표시됐다. 6의 모양이 강의노트 표와 달랐을 뿐 숫자는 모두 바르게 읽혔으므로 이번 실험의 목적은 달성했다고 본다.
실험 중 막혔던 부분은 없었고, 숫자 자체가 예상과 다르게 나온 경우도 없었다. 실험 1은 초기화 입력이 없어서 처음 켜지는 LED가 정해지지 않았는데, 촬영을 시작했을 때는 Y3이 켜져 있었다. 예비보고서에서 Y0이 켜진 구간을 기준으로 잡기로 해 두었기 때문에 순서를 확인하는 데는 문제가 없었고, 따로 회로를 바꾸어 해결한 부분도 없었다. 시작 상태를 정하는 방법은 추가 공부에 적었다.
새로 알게 된 점은 이번에 쓴 7447이 6을 a까지 켠 acdefg로, 9를 d가 빠진 abcfg로 표시한다는 것이다. 같은 숫자라도 디코더에 따라 켜지는 세그먼트가 다를 수 있으며, 그 근거는 결과 분석에 적었다. 또 7490이 9에서 다음 클럭을 받으면 A와 D가 함께 꺼지며 바로 0으로 돌아오는 것을 보면서, 2분주와 5분주를 이어 BCD로 계수하는 구조를 확인할 수 있었다.
예비보고서를 쓰면서 처음 배포된 강의노트 표시기 회로도의 FND 핀 번호가 강의노트 끝의 핀표와 맞지 않는다는 것을 발견해 핀표대로 결선했는데, 이후 조교 공지와 정정된 강의노트로 같은 결선이 정정 내용으로 안내되어 그 판단이 맞았음을 확인했다. 회로도를 그대로 따르기 전에 소자의 핀표와 대조해 보는 것이 필요하다는 것을 알게 됐다.
<empty-block/>
<empty-block/>
# 추가 공부
## 비동기 카운터의 시작 상태와 디코딩 글리치
실험 1에서 시작 LED가 정해지지 않은 것은 두 플립플롭의 PR과 CL을 모두 VCC에 묶었기 때문이다. 74HC76의 CL은 0일 때 Q를 0으로 만드는 비동기 입력이므로, 두 CL을 묶어 평소에는 VCC에 두고 시작할 때만 잠깐 GND로 내리는 스위치를 달면 AB=00에서 출발해 항상 Y0부터 켜지게 할 수 있다. 실험 3의 7490에서 R0이 맡은 역할과 같다.
비동기 구조에는 상태 사이의 짧은 중간 상태도 있다. AB가 10에서 01로 갈 때 A가 먼저 0으로 떨어지고 B는 A의 하강 에지를 받은 뒤 플립플롭의 전달 지연만큼 늦게 1이 된다. 그 사이에는 AB=00이 잠깐 만들어지므로 Y0이 아주 짧게 1이 될 수 있다. 같은 이유로 11에서 00으로 갈 때는 01을 지나 Y2가 잠깐 켜질 수 있다. 이 펄스는 나노초 단위라 LED로는 보이지 않았고 오실로스코프로 측정하지도 않았다. 다만 Y0\~Y3을 다른 플립플롭의 클럭이나 비동기 입력에 쓰면 이 짧은 펄스가 오동작을 일으킬 수 있다.
이를 피하려면 두 플립플롭에 같은 클럭을 넣는 동기식으로 바꾸면 된다. FFA는 J=K=1로 그대로 두고 FFB는 J=K=A로 연결하면 A가 1인 상태에서 하강 에지가 올 때만 B가 뒤집히므로, 순서는 그대로 00, 10, 01, 11이면서 A와 B가 같은 에지에서 함께 바뀐다. 두 출력의 지연 차이가 줄어 중간 상태가 생길 여지가 작아진다.
<empty-block/>
## 7447 출력 전류와 330Ω 세그먼트 저항
SN7447A의 세그먼트 출력은 오픈 컬렉터로, 데이터시트의 권장 동작 조건에서 켜진 상태의 출력 전류는 최대 40mA, 꺼진 상태에서 출력에 걸릴 수 있는 전압은 최대 15V다. 출력 전류 40mA를 흘릴 때 켜진 출력의 전압은 전형값 0.3V, 최대 0.4V로 보증된다.
이번 회로에서 세그먼트 하나에 흐르는 전류는 (5V − 세그먼트 LED의 순방향 전압 − 출력 전압) ÷ 330Ω이다. 이번 실험에서는 FND의 순방향 전압을 측정하지 않았으므로, 순방향 전압을 0으로 놓은 가장 불리한 경우를 따져 보면 (5V − 0.4V) ÷ 330Ω ≈ 13.9mA가 된다. 실제 전류는 이보다 작고, 40mA 한도의 절반에도 미치지 않는다. 출력 하나당 여유는 충분하다. 숫자 8처럼 일곱 세그먼트가 모두 켜지면 칩 전체로 최대 약 97mA가 FND의 공통 단자에서 7447을 거쳐 GND로 흐르므로, 5V 전원은 이 전류와 다른 IC의 전류를 함께 감당해야 한다.
꺼진 세그먼트 쪽은 FND 공통 단자가 5V이고 출력이 오픈 컬렉터라 출력 핀에 5V 이하만 걸려 15V 한도와 거리가 멀다. 다만 이 수치는 SN7447A의 것이고, 조교 공지가 74HC47로 적은 이번 칩은 출력 구조와 전류 한도가 다를 수 있다. 실물 칩의 제조사 데이터시트로 다시 확인이 필요하다.
<empty-block/>
<empty-block/>
# 출처 및 참고문헌
- 논리회로실험 강의노트
- 논리회로실험 IC 특성 분석 가이드
- Renesas Electronics. HD74HC76, Dual J-K Flip-Flops (with Preset and Clear). 문서번호 REJ03D0551-0200 (Previous ADE-205-423), Rev. 2.00, 2005-10-06. [https://www.renesas.com/en/document/dst/hd74hc76-datasheet](https://www.renesas.com/en/document/dst/hd74hc76-datasheet)
- Texas Instruments. SN74HC08, SN54HC08, Quadruple 2-Input AND Gates. 문서번호 SCLS081J, 1982-12 발행, 2025-02 개정. [https://www.ti.com/lit/ds/symlink/sn74hc08.pdf](https://www.ti.com/lit/ds/symlink/sn74hc08.pdf)
- Texas Instruments. SN7490A, SN74LS90, Decade, Divide-by-Twelve and Binary Counters. 문서번호 SDLS940A, 1974-03 발행, 1988-03 개정. [https://www.ti.com/lit/ds/symlink/sn74ls90.pdf](https://www.ti.com/lit/ds/symlink/sn74ls90.pdf)
- Texas Instruments. SN7447A, SN74LS47, BCD-to-Seven-Segment Decoders/Drivers. 문서번호 SDLS111, 1974-03 발행, 1988-03 개정. [https://www.ti.com/lit/ds/symlink/sn74ls47.pdf](https://www.ti.com/lit/ds/symlink/sn74ls47.pdf)