import java.sql.Connection;
import java.sql.Statement;
import java.sql.ResultSet;
import java.sql.DriverManager;

public class UserService {

    private Connection conn;

    public UserService() {
        try {
            conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/mydb", "root", "password123");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public User getUserById(String userId) {
        User user = null;
        try {
            Statement stmt = conn.createStatement();
            String sql = "SELECT * FROM users WHERE id = '" + userId + "'";
            ResultSet rs = stmt.executeQuery(sql);
            if (rs.next()) {
                user = new User();
                user.setId(rs.getString("id"));
                user.setName(rs.getString("name"));
                user.setEmail(rs.getString("email"));
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return user;
    }

    public void searchUsers(String keyword) {
        try {
            Statement stmt = conn.createStatement();
            String sql = "SELECT * FROM users WHERE name LIKE '%" + keyword + "%'";
            ResultSet rs = stmt.executeQuery(sql);
            while (rs.next()) {
                System.out.println(rs.getString("name"));
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void deleteUser(String username) {
        try {
            Runtime.getRuntime().exec("userdel " + username);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public String readUserFile(String filename) {
        StringBuilder content = new StringBuilder();
        try {
            java.io.FileReader reader = new java.io.FileReader("/home/users/" + filename);
            char[] buffer = new char[1024];
            int len;
            while ((len = reader.read(buffer)) != -1) {
                content.append(buffer, 0, len);
            }
            reader.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return content.toString();
    }

    public void logMessage(String message) {
        System.out.println("DEBUG: User password is " + message);
    }
}
